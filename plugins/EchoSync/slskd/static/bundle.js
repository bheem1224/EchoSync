//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1, t = !1;
function n() {
	t = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
n();
//#endregion
//#region node_modules/svelte/src/constants.js
var r = {}, i = Symbol("uninitialized"), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, ee = () => {};
function te(e) {
	return e();
}
function v(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function ne() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var y = 1024, b = 2048, x = 4096, re = 8192, ie = 16384, ae = 32768, oe = 1 << 25, se = 65536, ce = 1 << 19, le = 1 << 20, ue = 65536, de = 1 << 21, fe = 1 << 22, pe = 1 << 23, me = Symbol("$state"), he = Symbol("legacy props"), ge = Symbol(""), _e = Symbol("attributes"), ve = Symbol("class"), ye = Symbol("style"), be = Symbol("text"), xe = Symbol("form reset"), Se = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), Ce = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function we(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function Te() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Ee(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function De() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Oe(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function ke() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Ae() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function je(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Me() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Ne() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Pe() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Fe() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Ie() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Le(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Re() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var S = !1;
function ze(e) {
	S = e;
}
var C;
function w(e) {
	if (e === null) throw Le(), r;
	return C = e;
}
function Be() {
	return w(/* @__PURE__ */ I(C));
}
function T(e) {
	if (S) {
		if (/* @__PURE__ */ I(C) !== null) throw Le(), r;
		C = e;
	}
}
function Ve(e = 1) {
	if (S) {
		for (var t = e, n = C; t--;) n = /* @__PURE__ */ I(n);
		C = n;
	}
}
function He(e = !0) {
	for (var t = 0, n = C;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ I(n);
		e && n.remove(), n = i;
	}
}
function Ue(e) {
	if (!e || e.nodeType !== 8) throw Le(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function We(e) {
	return e === this.v;
}
function Ge(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Ke(e) {
	return !Ge(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var E = null;
function qe(e) {
	E = e;
}
function Je(e, n = !1, r) {
	E = {
		p: E,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: K,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Ye(e) {
	var t = E, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) bn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, E = t.p, e ?? {};
}
function Xe() {
	return !t || E !== null && E.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Ze = [];
function Qe() {
	var e = Ze;
	Ze = [], v(e);
}
function D(e) {
	if (Ze.length === 0 && !ft) {
		var t = Ze;
		queueMicrotask(() => {
			t === Ze && Qe();
		});
	}
	Ze.push(e);
}
function $e() {
	for (; Ze.length > 0;) Qe();
}
function et(e) {
	var t = K;
	if (t === null) return U.f |= pe, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	O(e, t);
}
function O(e, t) {
	for (; t !== null;) {
		if (t.f & 128) {
			if (!(t.f & 32768)) throw e;
			try {
				t.b.error(e);
				return;
			} catch (t) {
				e = t;
			}
		}
		t = t.parent;
	}
	throw e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var tt = ~(b | x | y);
function k(e, t) {
	e.f = e.f & tt | t;
}
function nt(e) {
	e.f & 512 || e.deps === null ? k(e, y) : k(e, x);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function rt(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= ue, rt(t.deps));
}
function it(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), rt(e.deps), k(e, y);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var at = !1, ot = !1;
function st(e) {
	var t = ot;
	try {
		return ot = !1, [e(), ot];
	} finally {
		ot = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var ct = null, lt = null, A = null, ut = null, j = null, dt = null, ft = !1, pt = !1, mt = null, ht = null, gt = 0, _t = 1, vt = class t {
	id = _t++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	unblocked = /* @__PURE__ */ new Set();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = /* @__PURE__ */ new Set();
	#o = 0;
	#s = /* @__PURE__ */ new Map();
	#c = null;
	#l = [];
	#u = [];
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Map();
	#m = /* @__PURE__ */ new Set();
	is_fork = !1;
	#h = !1;
	#g() {
		if (this.is_fork) return !0;
		for (let n of this.#s.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#p.has(e)) {
					t = !0;
					break;
				}
				e = e.parent;
			}
			if (!t) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#p.has(e) || this.#p.set(e, {
			d: [],
			m: []
		}), this.#m.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#p.get(e);
		if (n) {
			this.#p.delete(e);
			for (var r of n.d) k(r, b), t(r);
			for (r of n.m) k(r, x), t(r);
		}
		this.#m.add(e);
	}
	#_() {
		if (this.#e = !0, gt++ > 1e3 && (this.#w(), bt()), !this.#g()) {
			for (let e of this.#d) this.#f.delete(e), k(e, b), this.schedule(e);
			for (let e of this.#f) k(e, x), this.schedule(e);
		}
		let n = this.#l;
		this.#l = [], this.apply();
		var r = mt = [], i = [], a = ht = [];
		for (let e of n) try {
			this.#v(e, r, i);
		} catch (t) {
			throw Et(e), t;
		}
		if (A = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (mt = null, ht = null, this.#g()) {
			this.#x(i), this.#x(r);
			for (let [e, t] of this.#p) Tt(e, t);
			a.length > 0 && A.#_();
			return;
		}
		let s = this.#y();
		if (s) {
			s.#b(this);
			return;
		}
		this.#d.clear(), this.#f.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), ut = this, xt(i), xt(r), ut = null, this.#c?.resolve();
		var c = A;
		if (this.linked && this.#o === 0 && this.#w(), e && !this.linked && (this.#S(), A = c), this.#l.length > 0) {
			c === null && (c = this, this.#C());
			let e = c;
			e.#l.push(...this.#l.filter((t) => !e.#l.includes(t)));
		}
		c !== null && c.#_();
	}
	#v(t, n, r) {
		t.f ^= y;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#p.has(i)) && i.fn !== null) {
				o ? i.f ^= y : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : Yn(i) && (a & 16 && this.#f.add(i), er(i));
				var s = i.first;
				if (s !== null) {
					i = s;
					continue;
				}
			}
			for (; i !== null;) {
				var c = i.next;
				if (c !== null) {
					i = c;
					break;
				}
				i = i.parent;
			}
		}
	}
	#y() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#b(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve);
		}
		let t = (e) => {
			var n = e.reactions;
			if (n !== null) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#f.delete(i), k(i, b), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#w(), A = this, this.#_();
	}
	#x(e) {
		for (var t = 0; t < e.length; t += 1) it(e[t], this.#d, this.#f);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), j?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		A = this;
	}
	deactivate() {
		A = null, j = null;
	}
	flush() {
		try {
			pt = !0, A = this, this.#_();
		} finally {
			gt = 0, dt = null, mt = null, ht = null, pt = !1, A = null, j = null, Gt.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear(), this.#a.clear(), this.#w();
	}
	register_created_effect(e) {
		this.#u.push(e);
	}
	#S() {
		this.#w();
		for (let l = ct; l !== null; l = l.#n) {
			var e = l.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (l.current.has(r)) {
					var n = l.current.get(r)[0];
					if (e && i !== n) l.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			if (e) for (let [e, t] of this.async_deriveds) {
				let n = l.async_deriveds.get(e);
				n && t.promise.then(n.resolve);
			}
			if (l.#e) {
				var r = [...l.current.keys()].filter((e) => !this.current.has(e));
				if (r.length === 0) e && l.discard();
				else if (t.length > 0) {
					if (e) for (let e of this.#m) l.unskip_effect(e, (e) => {
						e.f & 4194320 ? l.schedule(e) : l.#x([e]);
					});
					l.activate();
					var i = /* @__PURE__ */ new Set(), a = /* @__PURE__ */ new Map();
					for (var o of t) St(o, r, i, a);
					a = /* @__PURE__ */ new Map();
					var s = [...l.current.keys()].filter((e) => this.current.has(e) ? this.current.get(e)[0] !== e.v : !0);
					if (s.length > 0) for (let e of this.#u) !(e.f & 155648) && Ct(e, s, a) && (e.f & 4194320 ? (k(e, b), l.schedule(e)) : l.#d.add(e));
					if (l.#l.length > 0 && !l.#h) {
						l.apply();
						for (var c of l.#l) l.#v(c, [], []);
						l.#l = [];
					}
					l.deactivate();
				}
			}
		}
	}
	increment(e, t) {
		if (this.#o += 1, e) {
			let e = this.#s.get(t) ?? 0;
			this.#s.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#o, e) {
			let e = this.#s.get(t) ?? 0;
			e === 1 ? this.#s.delete(t) : this.#s.set(t, e - 1);
		}
		this.#h || (this.#h = !0, D(() => {
			this.#h = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#d.add(t);
		for (let e of t) this.#f.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	on_fork_commit(e) {
		this.#a.add(e);
	}
	run_fork_commit_callbacks() {
		for (let e of this.#a) e(this);
		this.#a.clear();
	}
	settled() {
		return (this.#c ??= ne()).promise;
	}
	static ensure() {
		if (A === null) {
			let e = A = new t();
			e.#C(), !pt && !ft && D(() => {
				e.#e || e.flush();
			});
		}
		return A;
	}
	apply() {
		if (!e || !this.is_fork && this.#t === null && this.#n === null) {
			j = null;
			return;
		}
		j = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) j.set(e, t);
		for (let e = ct; e !== null; e = e.#n) if (!(e === this || e.is_fork)) {
			var t = !1;
			if (e.id < this.id) {
				for (let [n, [, r]] of e.current) if (!r && this.current.has(n)) {
					t = !0;
					break;
				}
			}
			if (!t) for (let [t, n] of e.previous) j.has(t) || j.set(t, n);
		}
	}
	schedule(t) {
		if (dt = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (mt !== null && n === K && (e || (U === null || !(U.f & 2)) && !at)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= y;
			}
		}
		this.#l.push(n);
	}
	#C() {
		lt === null ? ct = lt = this : (lt.#n = this, this.#t = lt), lt = this;
	}
	#w() {
		var e = this.#t, t = this.#n;
		e === null ? ct = t : e.#n = t, t === null ? lt = e : t.#t = e, this.linked = !1;
	}
};
function yt(e) {
	var t = ft;
	ft = !0;
	try {
		var n;
		for (e && (A !== null && !A.is_fork && A.flush(), n = e());;) {
			if ($e(), A === null) return n;
			A.flush();
		}
	} finally {
		ft = t;
	}
}
function bt() {
	try {
		ke();
	} catch (e) {
		O(e, dt);
	}
}
var M = null;
function xt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Yn(r) && (M = /* @__PURE__ */ new Set(), er(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && Nn(r), M?.size > 0)) {
				Gt.clear();
				for (let e of M) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) M.has(n) && (M.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || er(n);
					}
				}
				M.clear();
			}
		}
		M = null;
	}
}
function St(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? St(i, t, n, r) : e & 4194320 && !(e & 2048) && Ct(i, t, r) && (k(i, b), wt(i));
	}
}
function Ct(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && Ct(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function wt(e) {
	A.schedule(e);
}
function Tt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), k(e, y);
		for (var n = e.first; n !== null;) Tt(n, t), n = n.next;
	}
}
function Et(e) {
	k(e, y);
	for (var t = e.first; t !== null;) Et(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function Dt(e) {
	let t = 0, n = qt(0), r;
	return () => {
		_n() && (Q(n), En(() => (t === 0 && (r = ir(() => e(() => Xt(n)))), t += 1, () => {
			D(() => {
				--t, t === 0 && (r?.(), r = void 0, Xt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var Ot = se | ce;
function kt(e, t, n, r) {
	new At(e, t, n, r);
}
var At = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = S ? C : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = Dt(() => (this.#m = qt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = K;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = K.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = On(() => {
			if (S) {
				let e = this.#t;
				Be();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, Ot), S && (this.#e = C);
	}
	#g() {
		try {
			this.#a = B(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = B(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), D(() => {
			var e = this.#c = document.createDocumentFragment(), t = an();
			e.append(t), this.#a = this.#x(() => B(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, Pn(this.#o, () => {
				this.#o = null;
			}), this.#b(A));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Rn(this.#a, e);
				let t = this.#n.pending;
				this.#o = B(() => t(this.#e));
			} else this.#b(A);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		it(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = K, n = U, r = E;
		q(this.#i), G(this.#i), qe(this.#i.ctx);
		try {
			return vt.ensure(), e();
		} catch (e) {
			return et(e), null;
		} finally {
			q(t), G(n), qe(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && Pn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, D(() => {
			this.#d = !1, this.#m && Jt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Q(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		A?.is_fork ? (this.#a && A.skip_effect(this.#a), this.#o && A.skip_effect(this.#o), this.#s && A.skip_effect(this.#s), A.on_fork_commit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), S && (w(this.#t), Ve(), w(He()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Re();
				return;
			}
			r = !0, i && Fe(), this.#s !== null && Pn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				O(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return B(() => {
						var t = K;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return O(e, this.#i.parent), null;
				}
			}));
		};
		D(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				O(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => O(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function jt(e, t, n, r) {
	let i = Xe() ? Ft : Rt;
	var a = e.filter((e) => !e.settled);
	if (n.length === 0 && a.length === 0) {
		r(t.map(i));
		return;
	}
	var o = K, s = Mt(), c = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function l(e) {
		if (!(o.f & 16384)) {
			s();
			try {
				r(e);
			} catch (e) {
				O(e, o);
			}
			Nt();
		}
	}
	var u = Pt();
	if (n.length === 0) {
		c.then(() => l(t.map(i))).finally(u);
		return;
	}
	function d() {
		Promise.all(n.map((e) => /* @__PURE__ */ Lt(e))).then((e) => l([...t.map(i), ...e])).catch((e) => O(e, o)).finally(u);
	}
	c ? c.then(() => {
		s(), d(), Nt();
	}) : d();
}
function Mt() {
	var e = K, t = U, n = E, r = A;
	return function(i = !0) {
		q(e), G(t), qe(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function Nt(e = !0) {
	q(null), G(null), qe(null), e && A?.deactivate();
}
function Pt() {
	var e = K, t = e.b, n = A, r = t.is_rendered();
	return t.update_pending_count(1, n), n.increment(r, e), () => {
		t.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Ft(e) {
	var t = 2 | b;
	return K !== null && (K.f |= ce), {
		ctx: E,
		deps: null,
		effects: null,
		equals: We,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: K,
		ac: null
	};
}
var It = Symbol("obsolete");
/* @__NO_SIDE_EFFECTS__ */
function Lt(e, t, n) {
	let r = K;
	r === null && Te();
	var a = void 0, o = qt(i), s = !U, c = /* @__PURE__ */ new Set();
	return Tn(() => {
		var t = K, n = ne();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== Se && n.reject(e);
			}).finally(Nt);
		} catch (e) {
			n.reject(e), Nt();
		}
		var i = A;
		if (s) {
			if (t.f & 32768) var l = Pt();
			if (r.b.is_rendered()) i.async_deriveds.get(t)?.reject(It);
			else for (let e of c.values()) e.reject(It);
			c.add(n), i.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== It && (i.activate(), t ? (o.f |= pe, Jt(o, t)) : (o.f & 8388608 && (o.f ^= pe), Jt(o, e)), i.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), vn(() => {
		for (let e of c) e.reject(It);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Rt(e) {
	let t = /* @__PURE__ */ Ft(e);
	return t.equals = Ke, t;
}
function zt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function Bt(e) {
	var t, n = K, r = e.parent;
	if (!H && r !== null && e.v !== i && r.f & 24576) return Ie(), e.v;
	q(r);
	try {
		e.f &= ~ue, zt(e), t = Zn(e);
	} finally {
		q(n);
	}
	return t;
}
function Vt(e) {
	var t = Bt(e);
	if (!e.equals(t) && (e.wv = Jn(), (!A?.is_fork || e.deps === null) && (A === null ? e.v = t : (A.capture(e, t, !0), ut?.capture(e, t, !0)), e.deps === null))) {
		k(e, y);
		return;
	}
	H || (j === null ? nt(e) : (_n() || A?.is_fork) && j.set(e, t));
}
function Ht(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(Se), t.fn !== null && (t.teardown = ee), t.ac = null, $n(t, 0), An(t));
}
function Ut(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && er(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Wt = /* @__PURE__ */ new Set(), Gt = /* @__PURE__ */ new Map(), Kt = !1;
function qt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: We,
		rv: 0,
		wv: 0
	};
}
/* @__NO_SIDE_EFFECTS__ */
function N(e, t) {
	let n = qt(e, t);
	return Hn(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function P(e, n = !1, r = !0) {
	let i = qt(e);
	return n || (i.equals = Ke), t && r && E !== null && E.l !== null && (E.l.s ??= []).push(i), i;
}
function F(e, t, n = !1) {
	return U !== null && (!W || U.f & 131072) && Xe() && U.f & 4325394 && (J === null || !c.call(J, e)) && Pe(), Jt(e, n ? Qt(t) : t, ht);
}
function Jt(e, t, n = null) {
	if (!e.equals(t)) {
		Gt.set(e, H ? t : e.v);
		var r = vt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Bt(t), j === null && nt(t);
		}
		e.wv = Jn(), Zt(e, b, n), Xe() && K !== null && K.f & 1024 && !(K.f & 96) && (Z === null ? Un([e]) : Z.push(e)), !r.is_fork && Wt.size > 0 && !Kt && Yt();
	}
	return t;
}
function Yt() {
	Kt = !1;
	for (let e of Wt) {
		e.f & 1024 && k(e, x);
		let t;
		try {
			t = Yn(e);
		} catch {
			t = !0;
		}
		t && er(e);
	}
	Wt.clear();
}
function Xt(e) {
	F(e, e.v + 1);
}
function Zt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Xe(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === K)) {
			var l = (c & b) === 0;
			if (l && k(s, t), c & 131072) Wt.add(s);
			else if (c & 2) {
				var u = s;
				j?.delete(u), c & 65536 || (c & 512 && (K === null || !(K.f & 2097152)) && (s.f |= ue), Zt(u, x, n));
			} else if (l) {
				var d = s;
				c & 16 && M !== null && M.add(d), n === null ? wt(d) : n.push(d);
			}
		}
	}
}
function Qt(e) {
	if (typeof e != "object" || !e || me in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ N(0), s = null, c = Kn, l = (e) => {
		if (Kn === c) return e();
		var t = U, n = Kn;
		G(null), qn(c);
		var r = e();
		return G(t), qn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ N(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Me();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ N(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ N(i, s));
					n.set(t, e), Xt(a);
				}
			} else F(r, i), Xt(a);
			return !0;
		},
		get(t, r, a) {
			if (r === me) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ N(Qt(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = Q(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = Q(a));
			} else if (r === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== i) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === me) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || K !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ N(a ? Qt(e[t]) : i, s)), n.set(t, r)), Q(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ N(i, s)), n.set(p + "", m)) : F(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ N(void 0, s)), F(u, Qt(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => Qt(o));
				F(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), ee = Number(t);
					Number.isInteger(ee) && ee >= _.v && F(_, ee + 1);
				}
				Xt(a);
			}
			return !0;
		},
		ownKeys(e) {
			Q(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			Ne();
		}
	});
}
var $t, en, tn, nn;
function rn() {
	if ($t === void 0) {
		$t = window, en = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		tn = f(t, "firstChild").get, nn = f(t, "nextSibling").get, _(e) && (e[ve] = void 0, e[_e] = null, e[ye] = void 0, e.__e = void 0), _(n) && (n[be] = void 0);
	}
}
function an(e = "") {
	return document.createTextNode(e);
}
/* @__NO_SIDE_EFFECTS__ */
function on(e) {
	return tn.call(e);
}
/* @__NO_SIDE_EFFECTS__ */
function I(e) {
	return nn.call(e);
}
function L(e, t) {
	if (!S) return /* @__PURE__ */ on(e);
	var n = /* @__PURE__ */ on(C);
	if (n === null) n = C.appendChild(an());
	else if (t && n.nodeType !== 3) {
		var r = an();
		return n?.before(r), w(r), r;
	}
	return t && un(n), w(n), n;
}
function R(e, t = 1, n = !1) {
	let r = S ? C : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ I(r);
	if (!S) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = an();
			return r === null ? i?.after(a) : r.before(a), w(a), a;
		}
		un(r);
	}
	return w(r), r;
}
function sn(e) {
	e.textContent = "";
}
function cn() {
	return !e || M !== null ? !1 : (K.f & ae) !== 0;
}
function ln(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function un(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var dn = !1;
function fn() {
	dn || (dn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[xe]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function pn(e) {
	var t = U, n = K;
	G(null), q(null);
	try {
		return e();
	} finally {
		G(t), q(n);
	}
}
function mn(e, t, n, r = n) {
	e.addEventListener(t, () => pn(n));
	let i = e[xe];
	i ? e[xe] = () => {
		i(), r(!0);
	} : e[xe] = () => r(!0), fn();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function hn(e) {
	K === null && (U === null && Oe(e), De()), H && Ee(e);
}
function gn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function z(e, t) {
	var n = K;
	n !== null && n.f & 8192 && (e |= re);
	var r = {
		ctx: E,
		deps: null,
		nodes: null,
		f: e | b | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	A?.register_created_effect(r);
	var i = r;
	if (e & 4) mt === null ? vt.ensure().schedule(r) : mt.push(r);
	else if (t !== null) {
		try {
			er(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= se));
	}
	if (i !== null && (i.parent = n, n !== null && gn(i, n), U !== null && U.f & 2 && !(e & 64))) {
		var a = U;
		(a.effects ??= []).push(i);
	}
	return r;
}
function _n() {
	return U !== null && !W;
}
function vn(e) {
	let t = z(8, null);
	return k(t, y), t.teardown = e, t;
}
function yn(e) {
	hn("$effect");
	var t = K.f;
	if (!U && t & 32 && !(t & 32768)) {
		var n = E;
		(n.e ??= []).push(e);
	} else return bn(e);
}
function bn(e) {
	return z(4 | le, e);
}
function xn(e) {
	return hn("$effect.pre"), z(8 | le, e);
}
function Sn(e) {
	vt.ensure();
	let t = z(64 | ce, e);
	return () => {
		V(t);
	};
}
function Cn(e) {
	vt.ensure();
	let t = z(64 | ce, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Pn(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function wn(e) {
	return z(4, e);
}
function Tn(e) {
	return z(fe | ce, e);
}
function En(e, t = 0) {
	return z(8 | t, e);
}
function Dn(e, t = [], n = [], r = []) {
	jt(r, t, n, (t) => {
		z(8, () => e(...t.map(Q)));
	});
}
function On(e, t = 0) {
	return z(16 | t, e);
}
function B(e) {
	return z(32 | ce, e);
}
function kn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = H, n = U;
		Vn(!0), G(null);
		try {
			t.call(null);
		} finally {
			Vn(e), G(n);
		}
	}
}
function An(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && pn(() => {
			e.abort(Se);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function jn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Mn(e.nodes.start, e.nodes.end), n = !0), k(e, oe), An(e, t && !n), $n(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	kn(e), e.f ^= oe, e.f |= ie;
	var i = e.parent;
	i !== null && i.first !== null && Nn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Mn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ I(e);
		e.remove(), e = n;
	}
}
function Nn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Pn(e, t, n = !0) {
	var r = [];
	Fn(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Fn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= re;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				Fn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function In(e) {
	Ln(e, !0);
}
function Ln(e, t) {
	if (e.f & 8192) {
		e.f ^= re, e.f & 1024 || (k(e, b), vt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Ln(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Rn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ I(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var zn = null, Bn = !1, H = !1;
function Vn(e) {
	H = e;
}
var U = null, W = !1;
function G(e) {
	U = e;
}
var K = null;
function q(e) {
	K = e;
}
var J = null;
function Hn(t) {
	U !== null && (!e || U.f & 2) && (J === null ? J = [t] : J.push(t));
}
var Y = null, X = 0, Z = null;
function Un(e) {
	Z = e;
}
var Wn = 1, Gn = 0, Kn = Gn;
function qn(e) {
	Kn = e;
}
function Jn() {
	return ++Wn;
}
function Yn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~ue), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Yn(a) && Vt(a), a.wv > e.wv) return !0;
		}
		t & 512 && j === null && k(e, y);
	}
	return !1;
}
function Xn(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && J !== null && c.call(J, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Xn(o, n, !1) : n === o && (r ? k(o, b) : o.f & 1024 && k(o, x), wt(o));
	}
}
function Zn(e) {
	var t = Y, n = X, r = Z, i = U, a = J, o = E, s = W, c = Kn, l = e.f;
	Y = null, X = 0, Z = null, U = l & 96 ? null : e, J = null, qe(e.ctx), W = !1, Kn = ++Gn, e.ac !== null && (pn(() => {
		e.ac.abort(Se);
	}), e.ac = null);
	try {
		e.f |= de;
		var u = e.fn, d = u();
		e.f |= ae;
		var f = e.deps, p = A?.is_fork;
		if (Y !== null) {
			var m;
			if (p || $n(e, X), f !== null && X > 0) for (f.length = X + Y.length, m = 0; m < Y.length; m++) f[X + m] = Y[m];
			else e.deps = f = Y;
			if (_n() && e.f & 512) for (m = X; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && X < f.length && ($n(e, X), f.length = X);
		if (Xe() && Z !== null && !W && f !== null && !(e.f & 6146)) for (m = 0; m < Z.length; m++) Xn(Z[m], e);
		if (i !== null && i !== e) {
			if (Gn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Gn;
			if (t !== null) for (let e of t) e.rv = Gn;
			Z !== null && (r === null ? r = Z : r.push(...Z));
		}
		return e.f & 8388608 && (e.f ^= pe), d;
	} catch (e) {
		return et(e);
	} finally {
		e.f ^= de, Y = t, X = n, Z = r, U = i, J = a, qe(o), W = s, Kn = c;
	}
}
function Qn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (Y === null || !c.call(Y, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~ue), o.v !== i && nt(o), Ht(o), $n(o, 0);
	}
}
function $n(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Qn(e, n[r]);
}
function er(e) {
	var t = e.f;
	if (!(t & 16384)) {
		k(e, y);
		var n = K, r = Bn;
		K = e, Bn = !0;
		try {
			t & 16777232 ? jn(e) : An(e), kn(e);
			var i = Zn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Wn;
		} finally {
			Bn = r, K = n;
		}
	}
}
async function tr() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), yt();
}
function Q(e) {
	var t = (e.f & 2) != 0;
	if (zn?.add(e), U !== null && !W && !(K !== null && K.f & 16384) && (J === null || !c.call(J, e))) {
		var n = U.deps;
		if (U.f & 2097152) e.rv < Gn && (e.rv = Gn, Y === null && n !== null && n[X] === e ? X++ : Y === null ? Y = [e] : Y.push(e));
		else {
			U.deps ??= [], c.call(U.deps, e) || U.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [U] : c.call(r, U) || r.push(U);
		}
	}
	if (H && Gt.has(e)) return Gt.get(e);
	if (t) {
		var i = e;
		if (H) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || rr(i)) && (a = Bt(i)), Gt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !W && U !== null && (Bn || (U.f & 512) != 0), s = (i.f & ae) === 0;
		Yn(i) && (o && (i.f |= 512), Vt(i)), o && !s && (Ut(i), nr(i));
	}
	if (j?.has(e)) return j.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function nr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Ut(t), nr(t));
}
function rr(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Gt.has(t) || t.f & 2 && rr(t)) return !0;
	return !1;
}
function ir(e) {
	var t = W;
	try {
		return W = !0, e();
	} finally {
		W = t;
	}
}
function ar(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (me in e) or(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && me in n && or(n);
		}
	}
}
function or(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			or(e[n], t);
		} catch {}
		let n = g(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = p(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var sr = Symbol("events"), cr = /* @__PURE__ */ new Set(), lr = /* @__PURE__ */ new Set();
function ur(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || pr.call(t, e), !e.cancelBubble) return pn(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? D(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function dr(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = ur(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && vn(() => {
		t.removeEventListener(e, o, a);
	});
}
var fr = null;
function pr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	fr = e;
	var o = 0, s = fr === e && e[sr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[sr] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		d(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var u = U, f = K;
		G(null), q(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[sr]?.[r];
					g != null && (!a.disabled || e.target === a) && g.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble || h === t || h === null) break;
				a = h;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[sr] = t, delete e.currentTarget, G(u), q(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var mr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function hr(e) {
	return mr?.createHTML(e) ?? e;
}
function gr(e) {
	var t = ln("template");
	return t.innerHTML = hr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function _r(e, t) {
	var n = K;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/* @__NO_SIDE_EFFECTS__ */
function vr(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (S) return _r(C, null), C;
		i === void 0 && (i = gr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ on(i)));
		var t = r || en ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ on(t), s = t.lastChild;
			_r(o, s);
		} else _r(t, t);
		return t;
	};
}
function $(e, t) {
	if (S) {
		var n = K;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = C), Be();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var yr = ["touchstart", "touchmove"];
function br(e) {
	return yr.includes(e);
}
function xr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[be] ??= e.nodeValue) && (e[be] = n, e.nodeValue = `${n}`);
}
function Sr(e, t) {
	return Tr(e, t);
}
function Cr(e, t) {
	rn(), t.intro = t.intro ?? !1;
	let n = t.target, i = S, a = C;
	try {
		for (var o = /* @__PURE__ */ on(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ I(o);
		if (!o) throw r;
		ze(!0), w(o);
		let i = Tr(e, {
			...t,
			anchor: o
		});
		return ze(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && Ae(), rn(), sn(n), ze(!1), Sr(e, t);
	} finally {
		ze(i), w(a);
	}
}
var wr = /* @__PURE__ */ new Map();
function Tr(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	rn();
	var u = void 0, d = Cn(() => {
		var s = n ?? t.appendChild(an());
		kt(s, { pending: () => {} }, (t) => {
			Je({});
			var n = E;
			if (o && (n.c = o), a && (i.$$events = a), S && _r(t, null), u = e(t, i) || {}, S && (K.nodes.end = C, C === null || C.nodeType !== 8 || C.data !== "]")) throw Le(), r;
			Ye();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = br(r);
					for (let e of [t, document]) {
						var a = wr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), wr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, pr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(cr)), lr.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = wr.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, pr), r.delete(e), r.size === 0 && wr.delete(n)) : r.set(e, i);
			}
			lr.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return Er.set(u, d), u;
}
var Er = /* @__PURE__ */ new WeakMap();
function Dr(e, t) {
	let n = Er.get(e);
	return n ? (Er.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Or = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) In(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (V(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Rn(r, t), t.append(an()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Pn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = A, r = cn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = an();
			i.append(a), this.#n.set(e, {
				effect: B(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, B(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else S && (this.anchor = C), this.#a(n);
	}
};
function kr(e) {
	E === null && we("onMount"), t && E.l !== null ? Ar(E).m.push(e) : yn(() => {
		let t = ir(e);
		if (typeof t == "function") return t;
	});
}
function Ar(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function jr(e, t, n = !1) {
	var r;
	S && (r = C, Be());
	var i = new Or(e), a = n ? se : 0;
	function o(e, t) {
		if (S) {
			var n = Ue(r);
			if (e !== parseInt(n.substring(1))) {
				var a = He();
				w(a), i.anchor = a, ze(!1), i.ensure(e, t), ze(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	On(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Mr(e, t) {
	wn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = ln("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Nr = Symbol("is custom element"), Pr = Symbol("is html"), Fr = Ce ? "link" : "LINK";
function Ir(e) {
	if (S) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Lr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Lr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[xe] = n, D(n), fn();
	}
}
function Lr(e, t, n, r) {
	var i = Rr(e);
	S && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Fr) || i[t] !== (i[t] = n) && (t === "loading" && (e[ge] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Br(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Rr(e) {
	return e[_e] ??= {
		[Nr]: e.nodeName.includes("-"),
		[Pr]: e.namespaceURI === a
	};
}
var zr = /* @__PURE__ */ new Map();
function Br(e) {
	var t = e.getAttribute("is") || e.nodeName, n = zr.get(t);
	if (n) return n;
	zr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Vr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	mn(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = Hr(t) ? Ur(a) : a, r(a), A !== null && i.add(A), await tr(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (S && t.defaultValue !== t.value || ir(n) == null && t.value) && (r(Hr(t) ? Ur(t.value) : t.value), A !== null && i.add(A)), En(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? ut : A;
			if (i.has(a)) return;
		}
		Hr(t) && r === Ur(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function Hr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Ur(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Wr(e = !1) {
	let t = E, n = t.l.u;
	if (!n) return;
	let r = () => ar(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ Ft(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Q(i);
	}
	n.b.length && xn(() => {
		Gr(t, r), v(n.b);
	}), yn(() => {
		let e = ir(() => n.m.map(te));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && yn(() => {
		Gr(t, r), v(n.a);
	});
}
function Gr(e, t) {
	if (e.l.s) for (let t of e.l.s) Q(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function Kr(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = void 0, d = () => s && a ? (u ??= /* @__PURE__ */ Ft(i), Q(u)) : (l && (l = !1, c = s ? ir(i) : i), c);
	let p;
	if (o) {
		var m = me in e || he in e;
		p = f(e, n)?.set ?? (m && n in e ? (t) => e[n] = t : void 0);
	}
	var h, g = !1;
	o ? [h, g] = st(() => e[n]) : h = e[n], h === void 0 && i !== void 0 && (h = d(), p && (a && je(n), p(h)));
	var _ = a ? () => {
		var t = e[n];
		return t === void 0 ? d() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var ee = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || ee || g) && p(t ? _() : e), e) : _();
		});
	}
	var te = !1, v = (r & 1 ? Ft : Rt)(() => (te = !1, _()));
	o && Q(v);
	var ne = K;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Q(v) : a && o ? Qt(e) : e;
			return F(v, n), te = !0, c !== void 0 && (c = n), e;
		}
		return H && te || ne.f & 16384 ? v.v : Q(v);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function qr(e) {
	return new Jr(e);
}
var Jr = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ P(t, !1, !1);
			return n.set(e, r), r;
		};
		let i = new Proxy({
			...t.props || {},
			$$events: {}
		}, {
			get(e, t) {
				return Q(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === he ? !0 : (Q(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return F(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? Cr : Sr)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && yt(), this.#e = i.$$events;
		for (let e of Object.keys(this.#t)) e === "$set" || e === "$destroy" || e === "$on" || d(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(i, e);
		}, this.#t.$destroy = () => {
			Dr(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, Yr;
typeof HTMLElement == "function" && (Yr = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = ln("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = Zr(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Xr(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = qr({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = Sn(() => {
				En(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Xr(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Xr(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return u(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function Xr(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function Zr(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function Qr(e, t, n, r, i, a) {
	let o = class extends Yr {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return u(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return u(t).forEach((e) => {
		d(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = Xr(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (f(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		d(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region SlskdCard.svelte
var $r = /* @__PURE__ */ vr("<span class=\"status-badge success svelte-11uhbwz\">● Connected</span>"), ei = /* @__PURE__ */ vr("<span class=\"status-badge warning svelte-11uhbwz\">⚠ Disconnected</span>"), ti = /* @__PURE__ */ vr("<span class=\"status-badge active svelte-11uhbwz\">● Active</span>"), ni = /* @__PURE__ */ vr("<button class=\"btn-ghost small svelte-11uhbwz\">Activate</button>"), ri = /* @__PURE__ */ vr("<div class=\"loading-state svelte-11uhbwz\">Loading...</div>"), ii = /* @__PURE__ */ vr("<button class=\"btn-ghost svelte-11uhbwz\"> </button>"), ai = /* @__PURE__ */ vr("<div class=\"settings-section svelte-11uhbwz\"><h3 class=\"section-title svelte-11uhbwz\">Server Configuration</h3> <div class=\"form-grid svelte-11uhbwz\"><label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Server URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:5030\" class=\"input-field svelte-11uhbwz\"/> <span class=\"helper-text svelte-11uhbwz\">Enter your slskd server address (include port, default :5030)</span></label> <label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Server Name (Optional)</span> <input type=\"text\" placeholder=\"My slskd Server\" class=\"input-field svelte-11uhbwz\"/></label> <label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">API Key</span> <div class=\"password-wrapper svelte-11uhbwz\"><input placeholder=\"Enter API key\" class=\"input-field svelte-11uhbwz\"/> <button type=\"button\" class=\"toggle-visibility svelte-11uhbwz\"> </button></div> <span class=\"helper-text svelte-11uhbwz\">API key from slskd settings (Options → Security → API Keys)</span></label> <div class=\"actions-row svelte-11uhbwz\"><button class=\"btn-primary svelte-11uhbwz\"> </button> <!></div></div></div>"), oi = /* @__PURE__ */ vr("<section class=\"plugin-card svelte-11uhbwz\"><div class=\"card-header svelte-11uhbwz\"><div class=\"header-left svelte-11uhbwz\"><h2 class=\"card-title svelte-11uhbwz\">Slskd</h2> <div class=\"badges svelte-11uhbwz\"><span class=\"type-badge svelte-11uhbwz\">Download Client</span> <!> <!></div></div> <div class=\"header-right svelte-11uhbwz\"><!> <button class=\"btn-ghost svelte-11uhbwz\"> </button></div></div> <!></section>"), si = {
	hash: "svelte-11uhbwz",
	code: ".plugin-card.svelte-11uhbwz {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-11uhbwz {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-11uhbwz {display:flex;align-items:center;gap:16px;}.card-title.svelte-11uhbwz {margin:0;font-size:20px;font-weight:700;}.badges.svelte-11uhbwz {display:flex;gap:8px;}.type-badge.svelte-11uhbwz {font-size:10px;padding:2px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);border-radius:4px;font-weight:700;text-transform:uppercase;}.status-badge.svelte-11uhbwz {font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-11uhbwz {background:rgba(16, 185, 129, 0.15);color:#10b981;}.status-badge.warning.svelte-11uhbwz {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-11uhbwz {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.header-right.svelte-11uhbwz {display:flex;gap:8px;}.btn-ghost.svelte-11uhbwz {padding:8px 16px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.small.svelte-11uhbwz {padding:4px 12px;font-size:11px;font-weight:700;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;}.btn-ghost.svelte-11uhbwz:hover {background:var(--bg-surface-elevated);filter:brightness(1.2);}.btn-primary.svelte-11uhbwz {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-11uhbwz:hover {opacity:0.9;}.loading-state.svelte-11uhbwz {padding:24px;text-align:center;color:var(--text-secondary, #94a3b8);}.settings-section.svelte-11uhbwz {margin-top:16px;}.section-title.svelte-11uhbwz {margin:0 0 16px 0;font-size:16px;font-weight:600;}.form-grid.svelte-11uhbwz {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-11uhbwz {display:flex;flex-direction:column;gap:6px;}.field-label.svelte-11uhbwz {font-size:13px;color:var(--text-secondary, #94a3b8);}.input-field.svelte-11uhbwz {width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-11uhbwz:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.password-wrapper.svelte-11uhbwz {position:relative;display:flex;align-items:center;}.toggle-visibility.svelte-11uhbwz {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.helper-text.svelte-11uhbwz {font-size:11px;color:var(--text-secondary, #94a3b8);}.actions-row.svelte-11uhbwz {display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;}"
};
function ci(e, t) {
	Je(t, !1), Mr(e, si);
	let n = Kr(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(""), i = /* @__PURE__ */ P(""), a = /* @__PURE__ */ P(""), o = /* @__PURE__ */ P(!1), s = /* @__PURE__ */ P(!0), c = /* @__PURE__ */ P(!1), l = /* @__PURE__ */ P(!1), u = /* @__PURE__ */ P(!1), d = /* @__PURE__ */ P(!1), f = /* @__PURE__ */ P(!1), p = !1, m = /* @__PURE__ */ P(!1);
	kr(async () => {
		await _(), await h(), F(s, !1);
	});
	async function h() {
		try {
			F(m, (await (await fetch(`${n()}/providers/download-clients/active`)).json()).active_client === "slskd");
		} catch (e) {
			console.error("Failed to check active status:", e);
		}
	}
	async function g() {
		try {
			await fetch(`${n()}/providers/download-clients/activate`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ client: "slskd" })
			}), F(m, !0);
		} catch (e) {
			console.error("Failed to activate client:", e);
		}
	}
	async function _() {
		try {
			let e = await (await fetch(`${n()}/providers/soulseek/settings`)).json();
			e && (F(r, e.slskd_url || ""), F(a, e.server_name || ""), F(i, e.api_key || ""), F(f, e.has_api_key || !1), F(o, e.configured || !1));
		} catch (e) {
			console.error("Failed to load slskd settings:", e);
		}
	}
	async function ee() {
		if (!Q(r).trim()) {
			console.error("Server URL is required");
			return;
		}
		try {
			F(c, !0);
			let e = {
				slskd_url: Q(r),
				server_name: Q(a)
			};
			Q(i) && Q(i) !== "****" && (e.api_key = Q(i)), await fetch(`${n()}/providers/soulseek/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), await _();
		} catch (e) {
			console.error("Failed to save slskd settings:", e);
		} finally {
			F(c, !1);
		}
	}
	async function te() {
		if (Q(r).trim()) try {
			F(l, !0), (await (await fetch(`${n()}/providers/soulseek/connection/test`, { method: "POST" })).json())?.success ? (F(o, !0), await _()) : F(o, !1);
		} catch (e) {
			console.error("Failed to test slskd connection:", e), F(o, !1);
		} finally {
			F(l, !1);
		}
	}
	async function v() {
		let e = !Q(d);
		if (F(d, e), e && Q(f) && Q(i) === "****" && !p) try {
			let e = await (await fetch(`${n()}/providers/soulseek/settings/key`)).json();
			e && e.api_key ? (F(i, e.api_key), p = !0) : F(d, !1);
		} catch {
			F(d, !1);
		}
		!e && p && (F(i, "****"), p = !1);
	}
	var ne = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), yt();
		}
	};
	Wr();
	var y = oi(), b = L(y), x = L(b), re = R(L(x), 2), ie = R(L(re), 2), ae = (e) => {
		$(e, $r());
	}, oe = (e) => {
		$(e, ei());
	};
	jr(ie, (e) => {
		Q(o) ? e(ae) : Q(r) && e(oe, 1);
	});
	var se = R(ie, 2), ce = (e) => {
		$(e, ti());
	};
	jr(se, (e) => {
		Q(m) && e(ce);
	}), T(re), T(x);
	var le = R(x, 2), ue = L(le), de = (e) => {
		var t = ni();
		dr("click", t, g), $(e, t);
	};
	jr(ue, (e) => {
		!Q(m) && Q(o) && e(de);
	});
	var fe = R(ue, 2), pe = L(fe, !0);
	T(fe), T(le), T(b);
	var me = R(b, 2), he = (e) => {
		$(e, ri());
	}, ge = (e) => {
		var t = ai(), n = R(L(t), 2), o = L(n), s = R(L(o), 2);
		Ir(s), Ve(2), T(o);
		var u = R(o, 2), p = R(L(u), 2);
		Ir(p), T(u);
		var m = R(u, 2), h = R(L(m), 2), g = L(h);
		Ir(g);
		var _ = R(g, 2), ne = L(_, !0);
		T(_), T(h), Ve(2), T(m);
		var y = R(m, 2), b = L(y), x = L(b, !0);
		T(b);
		var re = R(b, 2), ie = (e) => {
			var t = ii(), n = L(t, !0);
			T(t), Dn(() => {
				t.disabled = Q(l), xr(n, Q(l) ? "Testing..." : "Test Connection");
			}), dr("click", t, te), $(e, t);
		};
		jr(re, (e) => {
			Q(r) && (Q(f) || Q(i)) && e(ie);
		}), T(y), T(n), T(t), Dn(() => {
			Lr(g, "type", Q(d) ? "text" : "password"), xr(ne, Q(d) ? "🙈" : "👁️"), b.disabled = Q(c), xr(x, Q(c) ? "Saving..." : "Save Settings");
		}), Vr(s, () => Q(r), (e) => F(r, e)), Vr(p, () => Q(a), (e) => F(a, e)), Vr(g, () => Q(i), (e) => F(i, e)), dr("click", _, v), dr("click", b, ee), $(e, t);
	};
	return jr(me, (e) => {
		Q(s) ? e(he) : Q(u) || e(ge, 1);
	}), T(y), Dn(() => xr(pe, Q(u) ? "Expand" : "Collapse")), dr("click", fe, () => F(u, !Q(u))), $(e, y), Ye(ne);
}
customElements.define("slskd-dashboard-card", Qr(ci, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { ci as default };

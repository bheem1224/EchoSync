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
var r = {}, i = Symbol("uninitialized"), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, v = () => {};
function y(e) {
	return e();
}
function b(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function x() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var S = 1024, C = 2048, w = 4096, ee = 8192, te = 16384, ne = 32768, T = 1 << 25, re = 65536, ie = 1 << 19, ae = 1 << 20, oe = 1 << 25, se = 65536, ce = 1 << 21, le = 1 << 22, ue = 1 << 23, de = Symbol("$state"), fe = Symbol("legacy props"), pe = Symbol(""), me = Symbol("attributes"), he = Symbol("class"), ge = Symbol("style"), _e = Symbol("text"), ve = Symbol("form reset"), ye = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), be = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function xe(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function Se() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Ce(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function we(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Te() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Ee(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function De() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Oe() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function ke(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Ae() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function je() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Me() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Ne() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Pe() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Fe(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Ie() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var E = !1;
function Le(e) {
	E = e;
}
var D;
function O(e) {
	if (e === null) throw Fe(), r;
	return D = e;
}
function Re() {
	return O(/* @__PURE__ */ cn(D));
}
function k(e) {
	if (E) {
		if (/* @__PURE__ */ cn(D) !== null) throw Fe(), r;
		D = e;
	}
}
function ze(e = 1) {
	if (E) {
		for (var t = e, n = D; t--;) n = /* @__PURE__ */ cn(n);
		D = n;
	}
}
function Be(e = !0) {
	for (var t = 0, n = D;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ cn(n);
		e && n.remove(), n = i;
	}
}
function Ve(e) {
	if (!e || e.nodeType !== 8) throw Fe(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function He(e) {
	return e === this.v;
}
function Ue(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function We(e) {
	return !Ue(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var A = null;
function Ge(e) {
	A = e;
}
function Ke(e, n = !1, r) {
	A = {
		p: A,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: G,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function qe(e) {
	var t = A, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) Cn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, A = t.p, e ?? {};
}
function Je() {
	return !t || A !== null && A.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Ye = [];
function Xe() {
	var e = Ye;
	Ye = [], b(e);
}
function Ze(e) {
	if (Ye.length === 0 && !ft) {
		var t = Ye;
		queueMicrotask(() => {
			t === Ye && Xe();
		});
	}
	Ye.push(e);
}
function Qe() {
	for (; Ye.length > 0;) Xe();
}
function $e(e) {
	var t = G;
	if (t === null) return H.f |= ue, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	et(e, t);
}
function et(e, t) {
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
var tt = ~(C | w | S);
function j(e, t) {
	e.f = e.f & tt | t;
}
function nt(e) {
	e.f & 512 || e.deps === null ? j(e, S) : j(e, w);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function rt(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= se, rt(t.deps));
}
function it(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), rt(e.deps), j(e, S);
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
var ct = null, lt = null, M = null, ut = null, N = null, dt = null, ft = !1, pt = !1, mt = null, ht = null, gt = 0, _t = 1, vt = class t {
	id = _t++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = 0;
	#o = /* @__PURE__ */ new Map();
	#s = null;
	#c = [];
	#l = [];
	#u = /* @__PURE__ */ new Set();
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Map();
	#p = /* @__PURE__ */ new Set();
	is_fork = !1;
	#m = !1;
	constructor() {
		lt === null ? ct = lt = this : (lt.#n = this, this.#t = lt), lt = this;
	}
	#h() {
		if (this.is_fork) return !0;
		for (let n of this.#o.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#f.has(e)) {
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
		this.#f.has(e) || this.#f.set(e, {
			d: [],
			m: []
		}), this.#p.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#f.get(e);
		if (n) {
			this.#f.delete(e);
			for (var r of n.d) j(r, C), t(r);
			for (r of n.m) j(r, w), t(r);
		}
		this.#p.add(e);
	}
	#g() {
		this.#e = !0, gt++ > 1e3 && (this.#S(), bt());
		for (let e of this.#u) this.#d.delete(e), j(e, C), this.schedule(e);
		for (let e of this.#d) j(e, w), this.schedule(e);
		let n = this.#c;
		this.#c = [], this.apply();
		var r = mt = [], i = [], a = ht = [];
		for (let e of n) try {
			this.#_(e, r, i);
		} catch (t) {
			throw Dt(e), this.#h() || this.discard(), t;
		}
		if (M = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (mt = null, ht = null, this.#h()) {
			this.#b(i), this.#b(r);
			for (let [e, t] of this.#f) Et(e, t);
			a.length > 0 && M.#g();
			return;
		}
		let s = this.#v();
		if (s) {
			this.#b(i), this.#b(r), s.#y(this);
			return;
		}
		this.#u.clear(), this.#d.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), ut = this, St(i), St(r), ut = null, this.#s?.resolve();
		var c = M;
		if (this.#a === 0 && (this.#c.length === 0 || c !== null) && (this.#S(), e && (this.#x(), M = c)), this.#c.length > 0) if (c !== null) {
			let e = c;
			e.#c.push(...this.#c.filter((t) => !e.#c.includes(t)));
		} else c = this;
		c !== null && c.#g();
	}
	#_(t, n, r) {
		t.f ^= S;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#f.has(i)) && i.fn !== null) {
				o ? i.f ^= S : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : tr(i) && (a & 16 && this.#d.add(i), or(i));
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
	#v() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#y(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve).catch(e.reject);
		}
		this.transfer_effects(e.#u, e.#d);
		let t = (e) => {
			var n = e.reactions;
			if (n !== null) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#d.delete(i), j(i, C), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#S(), M = this, this.#g();
	}
	#b(e) {
		for (var t = 0; t < e.length; t += 1) it(e[t], this.#u, this.#d);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), N?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		M = this;
	}
	deactivate() {
		M = null, N = null;
	}
	flush() {
		try {
			pt = !0, M = this, this.#g();
		} finally {
			gt = 0, dt = null, mt = null, ht = null, pt = !1, M = null, N = null, Kt.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear(), this.#S(), this.#s?.resolve();
	}
	register_created_effect(e) {
		this.#l.push(e);
	}
	#x() {
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
				n && t.promise.then(n.resolve).catch(n.reject);
			}
			if (l.#e) {
				var r = [...l.current.keys()].filter((e) => !l.current.get(e)[1] && !this.current.has(e));
				if (r.length === 0) e && l.discard();
				else if (t.length > 0) {
					if (e) for (let e of this.#p) l.unskip_effect(e, (e) => {
						e.f & 4194320 ? l.schedule(e) : l.#b([e]);
					});
					l.activate();
					var i = /* @__PURE__ */ new Set(), a = /* @__PURE__ */ new Map();
					for (var o of t) Ct(o, r, i, a);
					a = /* @__PURE__ */ new Map();
					var s = [...l.current].filter(([e, t]) => {
						let n = this.current.get(e);
						return n ? n[0] !== t[0] || n[1] !== t[1] : !0;
					}).map(([e]) => e);
					if (s.length > 0) for (let e of this.#l) !(e.f & 155648) && wt(e, s, a) && (e.f & 4194320 ? (j(e, C), l.schedule(e)) : l.#u.add(e));
					if (l.#c.length > 0 && !l.#m) {
						l.apply();
						for (var c of l.#c) l.#_(c, [], []);
						l.#c = [];
					}
					l.deactivate();
				}
			}
		}
	}
	increment(e, t) {
		if (this.#a += 1, e) {
			let e = this.#o.get(t) ?? 0;
			this.#o.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#a, e) {
			let e = this.#o.get(t) ?? 0;
			e === 1 ? this.#o.delete(t) : this.#o.set(t, e - 1);
		}
		this.#m || (this.#m = !0, Ze(() => {
			this.#m = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#u.add(t);
		for (let e of t) this.#d.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	settled() {
		return (this.#s ??= x()).promise;
	}
	static ensure() {
		if (M === null) {
			let e = M = new t();
			!pt && !ft && Ze(() => {
				e.#e || e.flush();
			});
		}
		return M;
	}
	apply() {
		if (!e || !this.is_fork && this.#t === null && this.#n === null) {
			N = null;
			return;
		}
		N = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) N.set(e, t);
		for (let e = ct; e !== null; e = e.#n) if (!(e === this || e.is_fork)) {
			var t = !1;
			if (e.id < this.id) {
				for (let [n, [, r]] of e.current) if (!r && this.current.has(n)) {
					t = !0;
					break;
				}
			}
			if (!t) for (let [t, n] of e.previous) N.has(t) || N.set(t, n);
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
			if (mt !== null && n === G && (e || (H === null || !(H.f & 2)) && !at)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= S;
			}
		}
		this.#c.push(n);
	}
	#S() {
		if (this.linked) {
			var e = this.#t, t = this.#n;
			e === null ? ct = t : e.#n = t, t === null ? lt = e : t.#t = e, this.linked = !1;
		}
	}
};
function yt(e) {
	var t = ft;
	ft = !0;
	try {
		var n;
		for (e && (M !== null && !M.is_fork && M.flush(), n = e());;) {
			if (Qe(), M === null) return n;
			M.flush();
		}
	} finally {
		ft = t;
	}
}
function bt() {
	try {
		De();
	} catch (e) {
		et(e, dt);
	}
}
var xt = null;
function St(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && tr(r) && (xt = /* @__PURE__ */ new Set(), or(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && In(r), xt?.size > 0)) {
				Kt.clear();
				for (let e of xt) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) xt.has(n) && (xt.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || or(n);
					}
				}
				xt.clear();
			}
		}
		xt = null;
	}
}
function Ct(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? Ct(i, t, n, r) : e & 4194320 && !(e & 2048) && wt(i, t, r) && (j(i, C), Tt(i));
	}
}
function wt(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && wt(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function Tt(e) {
	M.schedule(e);
}
function Et(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), j(e, S);
		for (var n = e.first; n !== null;) Et(n, t), n = n.next;
	}
}
function Dt(e) {
	j(e, S);
	for (var t = e.first; t !== null;) Dt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function Ot(e) {
	let t = 0, n = Jt(0), r;
	return () => {
		bn() && (Y(n), kn(() => (t === 0 && (r = X(() => e(() => Qt(n)))), t += 1, () => {
			Ze(() => {
				--t, t === 0 && (r?.(), r = void 0, Qt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var kt = re | ie;
function At(e, t, n, r) {
	new jt(e, t, n, r);
}
var jt = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = E ? D : null;
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
	#h = Ot(() => (this.#m = Jt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = jn(() => {
			if (E) {
				let e = this.#t;
				Re();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, kt), E && (this.#e = D);
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
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), Ze(() => {
			var e = this.#c = document.createDocumentFragment(), t = I();
			e.append(t), this.#a = this.#x(() => B(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, Ln(this.#o, () => {
				this.#o = null;
			}), this.#b(M));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Vn(this.#a, e);
				let t = this.#n.pending;
				this.#o = B(() => t(this.#e));
			} else this.#b(M);
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
		var t = G, n = H, r = A;
		Kn(this.#i), W(this.#i), Ge(this.#i.ctx);
		try {
			return vt.ensure(), e();
		} catch (e) {
			return $e(e), null;
		} finally {
			Kn(t), W(n), Ge(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && Ln(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Ze(() => {
			this.#d = !1, this.#m && Xt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Y(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		M?.is_fork ? (this.#a && M.skip_effect(this.#a), this.#o && M.skip_effect(this.#o), this.#s && M.skip_effect(this.#s), M.oncommit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), E && (O(this.#t), ze(), O(Be()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Ie();
				return;
			}
			r = !0, i && Ne(), this.#s !== null && Ln(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				et(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return B(() => {
						var t = G;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return et(e, this.#i.parent), null;
				}
			}));
		};
		Ze(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				et(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => et(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function Mt(e, t, n, r) {
	let i = Je() ? It : zt;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = G, c = Nt(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				et(e, s);
			}
			Pt();
		}
	}
	var d = Ft();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ Rt(e))).then(u).catch((e) => et(e, s)).finally(d);
	}
	l ? l.then(() => {
		c(), f(), Pt();
	}) : f();
}
function Nt() {
	var e = G, t = H, n = A, r = M;
	return function(i = !0) {
		Kn(e), W(t), Ge(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function Pt(e = !0) {
	Kn(null), W(null), Ge(null), e && M?.deactivate();
}
function Ft() {
	var e = G, t = e.b, n = M, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function It(e) {
	var t = 2 | C;
	return G !== null && (G.f |= ie), {
		ctx: A,
		deps: null,
		effects: null,
		equals: He,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: G,
		ac: null
	};
}
var Lt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function Rt(e, t, n) {
	let r = G;
	r === null && Se();
	var a = void 0, o = Jt(i), s = !H, c = /* @__PURE__ */ new Set();
	return On(() => {
		var t = G, n = x();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== ye && n.reject(e);
			}).finally(Pt);
		} catch (e) {
			n.reject(e), Pt();
		}
		var i = M;
		if (s) {
			if (t.f & 32768) var l = Ft();
			if (r.b?.is_rendered()) i.async_deriveds.get(t)?.reject(Lt);
			else for (let e of c.values()) e.reject(Lt);
			c.add(n), i.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== Lt && (i.activate(), t ? (o.f |= ue, Xt(o, t)) : (o.f & 8388608 && (o.f ^= ue), Xt(o, e)), i.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), xn(() => {
		for (let e of c) e.reject(Lt);
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
/*#__NO_SIDE_EFFECTS__*/
function zt(e) {
	let t = /* @__PURE__ */ It(e);
	return t.equals = We, t;
}
function Bt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function Vt(e) {
	var t, n = G, r = e.parent;
	if (!Wn && r !== null && e.v !== i && r.f & 24576) return Pe(), e.v;
	Kn(r);
	try {
		e.f &= ~se, Bt(e), t = rr(e);
	} finally {
		Kn(n);
	}
	return t;
}
function Ht(e) {
	var t = Vt(e);
	if (!e.equals(t) && (e.wv = er(), (!M?.is_fork || e.deps === null) && (M === null ? e.v = t : (M.capture(e, t, !0), ut?.capture(e, t, !0)), e.deps === null))) {
		j(e, S);
		return;
	}
	Wn || (N === null ? nt(e) : (bn() || M?.is_fork) && N.set(e, t));
}
function Ut(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(ye), t.fn !== null && (t.teardown = v), t.ac = null, ar(t, 0), Nn(t));
}
function Wt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && or(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Gt = /* @__PURE__ */ new Set(), Kt = /* @__PURE__ */ new Map(), qt = !1;
function Jt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: He,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Yt(e, t) {
	let n = Jt(e, t);
	return Jn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function P(e, n = !1, r = !0) {
	let i = Jt(e);
	return n || (i.equals = We), t && r && A !== null && A.l !== null && (A.l.s ??= []).push(i), i;
}
function F(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && Je() && H.f & 4325394 && (qn === null || !qn.has(e)) && Me(), Xt(e, n ? en(t) : t, ht);
}
function Xt(e, t, n = null) {
	if (!e.equals(t)) {
		Kt.set(e, Wn ? t : e.v);
		var r = vt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Vt(t), N === null && nt(t);
		}
		e.wv = er(), $t(e, C, n), Je() && G !== null && G.f & 1024 && !(G.f & 96) && (J === null ? Yn([e]) : J.push(e)), !r.is_fork && Gt.size > 0 && !qt && Zt();
	}
	return t;
}
function Zt() {
	qt = !1;
	for (let e of Gt) {
		e.f & 1024 && j(e, w);
		let t;
		try {
			t = tr(e);
		} catch {
			t = !0;
		}
		t && or(e);
	}
	Gt.clear();
}
function Qt(e) {
	F(e, e.v + 1);
}
function $t(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Je(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === G)) {
			var l = (c & C) === 0;
			if (l && j(s, t), c & 131072) Gt.add(s);
			else if (c & 2) {
				var u = s;
				N?.delete(u), c & 65536 || (c & 512 && (G === null || !(G.f & 2097152)) && (s.f |= se), $t(u, w, n));
			} else if (l) {
				var d = s;
				c & 16 && xt !== null && xt.add(d), n === null ? Tt(d) : n.push(d);
			}
		}
	}
}
function en(e) {
	if (typeof e != "object" || !e || de in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ Yt(0), s = null, c = Qn, l = (e) => {
		if (Qn === c) return e();
		var t = H, n = Qn;
		W(null), $n(c);
		var r = e();
		return W(t), $n(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ Yt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Ae();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Yt(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Yt(i, s));
					n.set(t, e), Qt(a);
				}
			} else F(r, i), Qt(a);
			return !0;
		},
		get(t, r, a) {
			if (r === de) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ Yt(en(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = Y(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = Y(a));
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
			if (t === de) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || G !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ Yt(a ? en(e[t]) : i, s)), n.set(t, r)), Y(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Yt(i, s)), n.set(p + "", m)) : F(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Yt(void 0, s)), F(u, en(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => en(o));
				F(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && F(_, v + 1);
				}
				Qt(a);
			}
			return !0;
		},
		ownKeys(e) {
			Y(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			je();
		}
	});
}
new Set([
	"copyWithin",
	"fill",
	"pop",
	"push",
	"reverse",
	"shift",
	"sort",
	"splice",
	"unshift"
]);
var tn, nn, rn, an;
function on() {
	if (tn === void 0) {
		tn = window, nn = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		rn = f(t, "firstChild").get, an = f(t, "nextSibling").get, _(e) && (e[he] = void 0, e[me] = null, e[ge] = void 0, e.__e = void 0), _(n) && (n[_e] = void 0);
	}
}
function I(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function sn(e) {
	return rn.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function cn(e) {
	return an.call(e);
}
function L(e, t) {
	if (!E) return /* @__PURE__ */ sn(e);
	var n = /* @__PURE__ */ sn(D);
	if (n === null) n = D.appendChild(I());
	else if (t && n.nodeType !== 3) {
		var r = I();
		return n?.before(r), O(r), r;
	}
	return t && pn(n), O(n), n;
}
function ln(e, t = !1) {
	if (!E) {
		var n = /* @__PURE__ */ sn(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ cn(n) : n;
	}
	if (t) {
		if (D?.nodeType !== 3) {
			var r = I();
			return D?.before(r), O(r), r;
		}
		pn(D);
	}
	return D;
}
function R(e, t = 1, n = !1) {
	let r = E ? D : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ cn(r);
	if (!E) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = I();
			return r === null ? i?.after(a) : r.before(a), O(a), a;
		}
		pn(r);
	}
	return O(r), r;
}
function un(e) {
	e.textContent = "";
}
function dn() {
	return !e || xt !== null ? !1 : (G.f & ne) !== 0;
}
function fn(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function pn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var mn = !1;
function hn() {
	mn || (mn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ve]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function gn(e) {
	var t = H, n = G;
	W(null), Kn(null);
	try {
		return e();
	} finally {
		W(t), Kn(n);
	}
}
function _n(e, t, n, r = n) {
	e.addEventListener(t, () => gn(n));
	let i = e[ve];
	i ? e[ve] = () => {
		i(), r(!0);
	} : e[ve] = () => r(!0), hn();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function vn(e) {
	G === null && (H === null && Ee(e), Te()), Wn && we(e);
}
function yn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function z(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= ee);
	var r = {
		ctx: A,
		deps: null,
		nodes: null,
		f: e | C | 512,
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
	M?.register_created_effect(r);
	var i = r;
	if (e & 4) mt === null ? vt.ensure().schedule(r) : mt.push(r);
	else if (t !== null) {
		try {
			or(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= re));
	}
	if (i !== null && (i.parent = n, n !== null && yn(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function bn() {
	return H !== null && !U;
}
function xn(e) {
	let t = z(8, null);
	return j(t, S), t.teardown = e, t;
}
function Sn(e) {
	vn("$effect");
	var t = G.f;
	if (!H && t & 32 && A !== null && !A.i) {
		var n = A;
		(n.e ??= []).push(e);
	} else return Cn(e);
}
function Cn(e) {
	return z(4 | ae, e);
}
function wn(e) {
	return vn("$effect.pre"), z(8 | ae, e);
}
function Tn(e) {
	vt.ensure();
	let t = z(64 | ie, e);
	return () => {
		V(t);
	};
}
function En(e) {
	vt.ensure();
	let t = z(64 | ie, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Ln(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function Dn(e) {
	return z(4, e);
}
function On(e) {
	return z(le | ie, e);
}
function kn(e, t = 0) {
	return z(8 | t, e);
}
function An(e, t = [], n = [], r = []) {
	Mt(r, t, n, (t) => {
		z(8, () => {
			e(...t.map(Y));
		});
	});
}
function jn(e, t = 0) {
	return z(16 | t, e);
}
function B(e) {
	return z(32 | ie, e);
}
function Mn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = Wn, n = H;
		Gn(!0), W(null);
		try {
			t.call(null);
		} finally {
			Gn(e), W(n);
		}
	}
}
function Nn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && gn(() => {
			e.abort(ye);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function Pn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Fn(e.nodes.start, e.nodes.end), n = !0), e.f |= T, Nn(e, t && !n), ar(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Mn(e), e.f ^= T, e.f |= te;
	var i = e.parent;
	i !== null && i.first !== null && In(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Fn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ cn(e);
		e.remove(), e = n;
	}
}
function In(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Ln(e, t, n = !0) {
	var r = [];
	Rn(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Rn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ee;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				Rn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function zn(e) {
	Bn(e, !0);
}
function Bn(e, t) {
	if (e.f & 8192) {
		e.f ^= ee, e.f & 1024 || (j(e, C), vt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Bn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Vn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ cn(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Hn = null, Un = !1, Wn = !1;
function Gn(e) {
	Wn = e;
}
var H = null, U = !1;
function W(e) {
	H = e;
}
var G = null;
function Kn(e) {
	G = e;
}
var qn = null;
function Jn(t) {
	H !== null && (!e || H.f & 2) && (qn ??= /* @__PURE__ */ new Set()).add(t);
}
var K = null, q = 0, J = null;
function Yn(e) {
	J = e;
}
var Xn = 1, Zn = 0, Qn = Zn;
function $n(e) {
	Qn = e;
}
function er() {
	return ++Xn;
}
function tr(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~se), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (tr(a) && Ht(a), a.wv > e.wv) return !0;
		}
		t & 512 && N === null && j(e, S);
	}
	return !1;
}
function nr(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && qn !== null && qn.has(t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? nr(o, n, !1) : n === o && (r ? j(o, C) : o.f & 1024 && j(o, w), Tt(o));
	}
}
function rr(e) {
	var t = K, n = q, r = J, i = H, a = qn, o = A, s = U, c = Qn, l = e.f;
	K = null, q = 0, J = null, H = l & 96 ? null : e, qn = null, Ge(e.ctx), U = !1, Qn = ++Zn, e.ac !== null && (gn(() => {
		e.ac.abort(ye);
	}), e.ac = null);
	try {
		e.f |= ce;
		var u = e.fn, d = u();
		e.f |= ne;
		var f = e.deps, p = M?.is_fork;
		if (K !== null) {
			var m;
			if (p || ar(e, q), f !== null && q > 0) for (f.length = q + K.length, m = 0; m < K.length; m++) f[q + m] = K[m];
			else e.deps = f = K;
			if (bn() && e.f & 512) for (m = q; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && q < f.length && (ar(e, q), f.length = q);
		if (Je() && J !== null && !U && f !== null && !(e.f & 6146)) for (m = 0; m < J.length; m++) nr(J[m], e);
		if (i !== null && i !== e) {
			if (Zn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Zn;
			if (t !== null) for (let e of t) e.rv = Zn;
			J !== null && (r === null ? r = J : r.push(...J));
		}
		return e.f & 8388608 && (e.f ^= ue), d;
	} catch (e) {
		return $e(e);
	} finally {
		e.f ^= ce, K = t, q = n, J = r, H = i, qn = a, Ge(o), U = s, Qn = c;
	}
}
function ir(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (K === null || !c.call(K, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~se), o.v !== i && nt(o), Ut(o), ar(o, 0);
	}
}
function ar(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) ir(e, n[r]);
}
function or(e) {
	var t = e.f;
	if (!(t & 16384)) {
		j(e, S);
		var n = G, r = Un;
		G = e, Un = !0;
		try {
			t & 16777232 ? Pn(e) : Nn(e), Mn(e);
			var i = rr(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Xn;
		} finally {
			Un = r, G = n;
		}
	}
}
async function sr() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), yt();
}
function Y(e) {
	var t = (e.f & 2) != 0;
	if (Hn?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (qn === null || !qn.has(e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < Zn && (e.rv = Zn, K === null && n !== null && n[q] === e ? q++ : K === null ? K = [e] : K.push(e));
		else {
			H.deps ??= [], c.call(H.deps, e) || H.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : c.call(r, H) || r.push(H);
		}
	}
	if (Wn && Kt.has(e)) return Kt.get(e);
	if (t) {
		var i = e;
		if (Wn) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || lr(i)) && (a = Vt(i)), Kt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !U && H !== null && (Un || (H.f & 512) != 0), s = (i.f & ne) === 0;
		tr(i) && (o && (i.f |= 512), Ht(i)), o && !s && (Wt(i), cr(i));
	}
	if (N?.has(e)) return N.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function cr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Wt(t), cr(t));
}
function lr(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Kt.has(t) || t.f & 2 && lr(t)) return !0;
	return !1;
}
function X(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function ur(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (de in e) dr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && de in n && dr(n);
		}
	}
}
function dr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			dr(e[n], t);
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
var fr = Symbol("events"), pr = /* @__PURE__ */ new Set(), mr = /* @__PURE__ */ new Set();
function hr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || _r.call(t, e), !e.cancelBubble) return gn(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? Ze(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function Z(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = hr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && xn(() => {
		t.removeEventListener(e, o, a);
	});
}
var gr = null;
function _r(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	gr = e;
	var o = 0, s = gr === e && e[fr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[fr] = t;
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
		var u = H, f = G;
		W(null), Kn(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[fr]?.[r];
					h != null && (!a.disabled || e.target === a) && h.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble) break;
				o++, a = o < i.length ? i[o] : null;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[fr] = t, delete e.currentTarget, W(u), Kn(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var vr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function yr(e) {
	return vr?.createHTML(e) ?? e;
}
function br(e) {
	var t = fn("template");
	return t.innerHTML = yr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function xr(e, t) {
	var n = G;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Q(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (E) return xr(D, null), D;
		i === void 0 && (i = br(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ sn(i)));
		var t = r || nn ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ sn(t), s = t.lastChild;
			xr(o, s);
		} else xr(t, t);
		return t;
	};
}
function $(e, t) {
	if (E) {
		var n = G;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = D), Re();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var Sr = ["touchstart", "touchmove"];
function Cr(e) {
	return Sr.includes(e);
}
function wr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[_e] ??= e.nodeValue) && (e[_e] = n, e.nodeValue = `${n}`);
}
function Tr(e, t) {
	return Or(e, t);
}
function Er(e, t) {
	on(), t.intro = t.intro ?? !1;
	let n = t.target, i = E, a = D;
	try {
		for (var o = /* @__PURE__ */ sn(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ cn(o);
		if (!o) throw r;
		Le(!0), O(o);
		let i = Or(e, {
			...t,
			anchor: o
		});
		return Le(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && Oe(), on(), un(n), Le(!1), Tr(e, t);
	} finally {
		Le(i), O(a);
	}
}
var Dr = /* @__PURE__ */ new Map();
function Or(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	on();
	var u = void 0, d = En(() => {
		var s = n ?? t.appendChild(I());
		At(s, { pending: () => {} }, (t) => {
			Ke({});
			var n = A;
			if (o && (n.c = o), a && (i.$$events = a), E && xr(t, null), u = e(t, i) || {}, E && (G.nodes.end = D, D === null || D.nodeType !== 8 || D.data !== "]")) throw Fe(), r;
			qe();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = Cr(r);
					for (let e of [t, document]) {
						var a = Dr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), Dr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, _r, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(pr)), mr.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = Dr.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, _r), r.delete(e), r.size === 0 && Dr.delete(n)) : r.set(e, i);
			}
			mr.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return kr.set(u, d), u;
}
var kr = /* @__PURE__ */ new WeakMap();
function Ar(e, t) {
	let n = kr.get(e);
	return n ? (kr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var jr = class {
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
			if (n) zn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (zn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
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
						Vn(r, t), t.append(I()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Ln(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = M, r = dn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = I();
			i.append(a), this.#n.set(e, {
				effect: B(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, B(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else E && (this.anchor = D), this.#a(n);
	}
};
function Mr(e) {
	A === null && xe("onMount"), t && A.l !== null ? Nr(A).m.push(e) : Sn(() => {
		let t = X(e);
		if (typeof t == "function") return t;
	});
}
function Nr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Pr(e, t, n = !1) {
	var r;
	E && (r = D, Re());
	var i = new jr(e), a = n ? re : 0;
	function o(e, t) {
		if (E) {
			var n = Ve(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Be();
				O(a), i.anchor = a, Le(!1), i.ensure(e, t), Le(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	jn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/each.js
function Fr(e, t) {
	return t;
}
function Ir(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		Ln(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Lr(e, l(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var c = r.length === 0 && n !== null;
		if (c) {
			var u = n, d = u.parentNode;
			un(d), d.append(u), e.items.clear();
		}
		Lr(e, t, !c);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Lr(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= oe, Vn(a, document.createDocumentFragment())) : V(t[i], n);
	}
}
var Rr;
function zr(e, t, n, r, i, a = null) {
	var s = e, c = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = E ? O(/* @__PURE__ */ sn(u)) : u.appendChild(I());
	}
	E && Re();
	var d = null, f = /* @__PURE__ */ zt(() => {
		var e = n();
		return o(e) ? e : e == null ? [] : l(e);
	}), p, m = /* @__PURE__ */ new Map(), h = !0;
	function g(e) {
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, Vr(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= oe, Ur(d, null, s)) : zn(d) : Ln(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: jn(() => {
			p = Y(f);
			var e = p.length;
			let o = !1;
			E && Ve(s) === "[!" != (e === 0) && (s = Be(), O(s), Le(!1), o = !0);
			for (var l = /* @__PURE__ */ new Set(), u = M, v = dn(), y = 0; y < e; y += 1) {
				E && D.nodeType === 8 && D.data === "]" && (s = D, o = !0, Le(!1));
				var b = p[y], x = r(b, y), S = h ? null : c.get(x);
				S ? (S.v && Xt(S.v, b), S.i && Xt(S.i, y), v && u.unskip_effect(S.e)) : (S = Hr(c, h ? s : Rr ??= I(), b, x, y, i, t, n), h || (S.e.f |= oe), c.set(x, S)), l.add(x);
			}
			if (e === 0 && a && !d && (h ? d = B(() => a(s)) : (d = B(() => a(Rr ??= I())), d.f |= oe)), e > l.size && Ce("", "", ""), E && e > 0 && O(Be()), !h) if (m.set(u, l), v) {
				for (let [e, t] of c) l.has(e) || u.skip_effect(t.e);
				u.oncommit(g), u.ondiscard(_);
			} else g(u);
			o && Le(!0), Y(f);
		}),
		flags: t,
		items: c,
		pending: m,
		outrogroups: null,
		fallback: d
	};
	h = !1, E && (s = D);
}
function Br(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function Vr(e, t, n, r, i) {
	var a = (r & 8) != 0, o = t.length, s = e.items, c = Br(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (zn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) if (_.f ^= oe, _ === c) Ur(_, null, n);
		else {
			var y = d ? d.next : c;
			_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), Wr(e, d, _), Wr(e, _, y), Ur(_, y, n), d = _, p = [], m = [], c = Br(d.next);
			continue;
		}
		if (_ !== c) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) Ur(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					Wr(e, S.prev, C.next), Wr(e, d, S), Wr(e, C, b), c = b, d = C, --v, p = [], m = [];
				} else u.delete(_), Ur(_, c, n), Wr(e, _.prev, _.next), Wr(e, _, d === null ? e.effect.first : d.next), Wr(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; c !== null && c !== _;) (u ??= /* @__PURE__ */ new Set()).add(c), m.push(c), c = Br(c.next);
			if (c === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, c = Br(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Lr(e, l(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (c !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; c !== null;) !(c.f & 8192) && c !== e.fallback && w.push(c), c = Br(c.next);
		var ee = w.length;
		if (ee > 0) {
			var te = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.fix();
			}
			Ir(e, w, te);
		}
	}
	a && Ze(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function Hr(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Jt(n) : /* @__PURE__ */ P(n, !1, !1) : null, l = o & 2 ? Jt(i) : null;
	return {
		v: c,
		i: l,
		e: B(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Ur(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ cn(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function Wr(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Gr(e, t) {
	Dn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = fn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/shared/attributes.js
var Kr = [..." 	\n\r\f\xA0\v﻿"];
function qr(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Kr.includes(r[o - 1])) && (s === r.length || Kr.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/class.js
function Jr(e, t, n, r, i, a) {
	var o = e[he];
	if (E || o !== n || o === void 0) {
		var s = qr(n, r, a);
		(!E || s !== e.getAttribute("class")) && (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e[he] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Yr = Symbol("is custom element"), Xr = Symbol("is html"), Zr = be ? "link" : "LINK", Qr = be ? "progress" : "PROGRESS";
function $r(e) {
	if (E) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					ti(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					ti(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ve] = n, Ze(n), hn();
	}
}
function ei(e, t) {
	var n = ni(e);
	n.value === (n.value = t ?? void 0) || e.value === t && (t !== 0 || e.nodeName !== Qr) || (e.value = t ?? "");
}
function ti(e, t, n, r) {
	var i = ni(e);
	E && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Zr) || i[t] !== (i[t] = n) && (t === "loading" && (e[pe] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && ii(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function ni(e) {
	return e[me] ??= {
		[Yr]: e.nodeName.includes("-"),
		[Xr]: e.namespaceURI === a
	};
}
var ri = /* @__PURE__ */ new Map();
function ii(e) {
	var t = e.getAttribute("is") || e.nodeName, n = ri.get(t);
	if (n) return n;
	ri.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function ai(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	_n(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = oi(t) ? si(a) : a, r(a), M !== null && i.add(M), await sr(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (E && t.defaultValue !== t.value || X(n) == null && t.value) && (r(oi(t) ? si(t.value) : t.value), M !== null && i.add(M)), kn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? ut : M;
			if (i.has(a)) return;
		}
		oi(t) && r === si(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function oi(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function si(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function ci(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function li(e = !1) {
	let t = A, n = t.l.u;
	if (!n) return;
	let r = () => ur(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ It(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Y(i);
	}
	n.b.length && wn(() => {
		ui(t, r), b(n.b);
	}), Sn(() => {
		let e = X(() => n.m.map(y));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && Sn(() => {
		ui(t, r), b(n.a);
	});
}
function ui(e, t) {
	if (e.l.s) for (let t of e.l.s) Y(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/misc.js
function di(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of o(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function fi(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = void 0, d = () => s && a ? (u ??= /* @__PURE__ */ It(i), Y(u)) : (l && (l = !1, c = s ? X(i) : i), c);
	let p;
	if (o) {
		var m = de in e || fe in e;
		p = f(e, n)?.set ?? (m && n in e ? (t) => e[n] = t : void 0);
	}
	var h, g = !1;
	o ? [h, g] = st(() => e[n]) : h = e[n], h === void 0 && i !== void 0 && (h = d(), p && (a && ke(n), p(h)));
	var _ = a ? () => {
		var t = e[n];
		return t === void 0 ? d() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var v = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || v || g) && p(t ? _() : e), e) : _();
		});
	}
	var y = !1, b = (r & 1 ? It : zt)(() => (y = !1, _()));
	o && Y(b);
	var x = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Y(b) : a && o ? en(e) : e;
			return F(b, n), y = !0, c !== void 0 && (c = n), e;
		}
		return Wn && y || x.f & 16384 ? b.v : Y(b);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function pi(e) {
	return new mi(e);
}
var mi = class {
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
				return Y(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === fe ? !0 : (Y(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return F(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? Er : Tr)(t.component, {
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
			Ar(this.#t);
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
}, hi;
typeof HTMLElement == "function" && (hi = class extends HTMLElement {
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
					let n = fn("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = _i(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = gi(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = pi({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = Tn(() => {
				kn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = gi(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = gi(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
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
function gi(e, t, n, r) {
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
function _i(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function vi(e, t, n, r, i, a) {
	let o = class extends hi {
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
				n = gi(e, n, t), this.$$d[e] = n;
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
//#region MusicBrainzCard.svelte
var yi = /* @__PURE__ */ Q("<div class=\"loading-state svelte-1ghyjz5\">Loading...</div>"), bi = /* @__PURE__ */ Q("<div class=\"redirect-copy-group svelte-1ghyjz5\"><input type=\"text\" class=\"input-field readonly svelte-1ghyjz5\" readonly=\"\"/> <button class=\"btn-primary svelte-1ghyjz5\">Copy</button></div>"), xi = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-1ghyjz5\">+ Add Account</button>"), Si = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-1ghyjz5\">✓ Authenticated</span>"), Ci = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-1ghyjz5\">⚠ Not Authenticated</span>"), wi = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-1ghyjz5\">● Active</span>"), Ti = /* @__PURE__ */ Q("<div class=\"account-item svelte-1ghyjz5\"><div class=\"account-info svelte-1ghyjz5\"><div class=\"account-name svelte-1ghyjz5\"> </div> <div class=\"account-badges svelte-1ghyjz5\"><!> <!></div></div> <div class=\"account-actions svelte-1ghyjz5\"><button class=\"link-btn svelte-1ghyjz5\"> </button> <button> </button> <button class=\"btn-danger svelte-1ghyjz5\">✕</button></div></div>"), Ei = /* @__PURE__ */ Q("<div class=\"empty-accounts svelte-1ghyjz5\">No accounts linked.</div>"), Di = /* @__PURE__ */ Q("<div class=\"settings-section svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">Server Configuration</h3> <div class=\"form-grid svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">API Base URL</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"https://musicbrainz.org/ws/2\"/> <p class=\"helper-text svelte-1ghyjz5\">Point this to a local MusicBrainz container for offline use.</p></label> <button class=\"btn-primary svelte-1ghyjz5\">Save Settings</button></div></div> <div class=\"settings-section svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">OAuth Credentials</h3> <div class=\"form-grid svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Client ID</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"Enter Client ID\"/></label> <label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Client Secret</span> <div class=\"password-wrapper svelte-1ghyjz5\"><input class=\"input-field svelte-1ghyjz5\"/> <button class=\"toggle-visibility svelte-1ghyjz5\"> </button></div></label> <button class=\"btn-primary svelte-1ghyjz5\"> </button></div></div> <div class=\"settings-section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">Redirect URI</h3> <button class=\"btn-ghost svelte-1ghyjz5\"> </button></div> <!></div> <div class=\"settings-section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\"> </h3> <!></div> <div class=\"accounts-list svelte-1ghyjz5\"></div></div>", 1), Oi = /* @__PURE__ */ Q("<div class=\"modal-overlay svelte-1ghyjz5\"><div class=\"modal-content svelte-1ghyjz5\"><div class=\"modal-header svelte-1ghyjz5\"><h3 class=\"modal-title svelte-1ghyjz5\">Add MusicBrainz Account</h3> <button class=\"close-btn svelte-1ghyjz5\">✕</button></div> <div class=\"modal-body svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Display Name</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"My Account\"/></label></div> <div class=\"modal-footer svelte-1ghyjz5\"><button class=\"btn-ghost svelte-1ghyjz5\">Cancel</button> <button class=\"btn-primary svelte-1ghyjz5\">Add</button></div></div></div>"), ki = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-1ghyjz5\"><div class=\"card-header svelte-1ghyjz5\"><div class=\"header-left svelte-1ghyjz5\"><h2 class=\"card-title svelte-1ghyjz5\">MusicBrainz</h2> <span class=\"type-badge svelte-1ghyjz5\">Metadata Provider</span></div></div> <!></section> <!>", 1), Ai = {
	hash: "svelte-1ghyjz5",
	code: ".plugin-card.svelte-1ghyjz5 {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-1ghyjz5 {display:flex;align-items:center;gap:12px;}.card-title.svelte-1ghyjz5 {margin:0;font-size:20px;font-weight:700;}.type-badge.svelte-1ghyjz5 {font-size:11px;padding:4px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-1ghyjz5 {padding:24px;text-align:center;color:var(--text-secondary, #cbd5e1);}.settings-section.svelte-1ghyjz5 {margin-bottom:24px;}.section-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;}.section-title.svelte-1ghyjz5 {margin:0;font-size:16px;font-weight:600;}.form-grid.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.field-label.svelte-1ghyjz5 {font-size:13px;font-weight:500;color:var(--text-secondary, #cbd5e1);}.input-field.svelte-1ghyjz5 {width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-1ghyjz5:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.input-field.readonly.svelte-1ghyjz5 {opacity:0.6;cursor:not-allowed;}.btn-primary.svelte-1ghyjz5 {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-1ghyjz5:hover:not(:disabled) {opacity:0.9;}.btn-primary.svelte-1ghyjz5:disabled {opacity:0.5;cursor:not-allowed;}.btn-ghost.svelte-1ghyjz5 {padding:8px 16px;background:rgba(255, 255, 255, 0.05);border:1px solid rgba(255, 255, 255, 0.1);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.svelte-1ghyjz5:hover {background:rgba(255, 255, 255, 0.1);}.btn-ghost.active.svelte-1ghyjz5 {border-color:var(--color-primary, #14b8a6);color:var(--color-primary, #14b8a6);}.btn-danger.svelte-1ghyjz5 {background:rgba(239, 68, 68, 0.15);color:#ef4444;border:none;padding:8px 12px;border-radius:6px;cursor:pointer;}.helper-text.svelte-1ghyjz5 {font-size:11px;color:var(--text-secondary, #cbd5e1);margin-top:4px;}.redirect-copy-group.svelte-1ghyjz5 {display:flex;gap:8px;align-items:stretch;}.redirect-copy-group.svelte-1ghyjz5 .input-field:where(.svelte-1ghyjz5) {flex:1;font-family:monospace;}.accounts-list.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.account-item.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:rgba(255, 255, 255, 0.03);border:1px solid rgba(255, 255, 255, 0.05);border-radius:8px;}.account-info.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:4px;}.account-name.svelte-1ghyjz5 {font-weight:600;font-size:14px;}.account-badges.svelte-1ghyjz5 {display:flex;gap:8px;}.status-badge.svelte-1ghyjz5 {font-size:10px;padding:2px 6px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-1ghyjz5 {background:rgba(34, 197, 94, 0.15);color:#22c55e;}.status-badge.warning.svelte-1ghyjz5 {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-1ghyjz5 {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.account-actions.svelte-1ghyjz5 {display:flex;gap:12px;align-items:center;}.link-btn.svelte-1ghyjz5 {background:none;border:none;color:var(--color-primary, #14b8a6);font-size:13px;font-weight:600;cursor:pointer;}.link-btn.svelte-1ghyjz5:hover {text-decoration:underline;}.password-wrapper.svelte-1ghyjz5 {position:relative;display:flex;align-items:center;width:100%;}.toggle-visibility.svelte-1ghyjz5 {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.modal-overlay.svelte-1ghyjz5 {position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:1000;backdrop-filter:blur(4px);}.modal-content.svelte-1ghyjz5 {background:#0f1216;border:1px solid var(--border-subtle, #1e293b);border-radius:12px;width:100%;max-width:440px;box-shadow:0 24px 48px rgba(0,0,0,0.5);}.modal-header.svelte-1ghyjz5 {padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;justify-content:space-between;align-items:center;}.modal-title.svelte-1ghyjz5 {margin:0;font-size:16px;font-weight:700;}.close-btn.svelte-1ghyjz5 {background:none;border:none;color:var(--text-secondary, #cbd5e1);font-size:20px;cursor:pointer;}.modal-body.svelte-1ghyjz5 {padding:20px;display:flex;flex-direction:column;gap:16px;}.modal-footer.svelte-1ghyjz5 {padding:16px 20px;border-top:1px solid rgba(255,255,255,0.05);display:flex;justify-content:flex-end;gap:12px;}.empty-accounts.svelte-1ghyjz5 {text-align:center;padding:16px;color:var(--text-secondary, #cbd5e1);font-size:13px;background:rgba(255, 255, 255, 0.02);border-radius:8px;border:1px dashed rgba(255, 255, 255, 0.1);}"
};
function ji(e, t) {
	Ke(t, !1), Gr(e, Ai);
	let n = fi(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(!0), i = /* @__PURE__ */ P([]), a = /* @__PURE__ */ P(""), o = /* @__PURE__ */ P(""), s = /* @__PURE__ */ P(""), c = /* @__PURE__ */ P(""), l = !1, u = !1, d = /* @__PURE__ */ P(!1), f = /* @__PURE__ */ P(!1), p = /* @__PURE__ */ P(!1), m = /* @__PURE__ */ P("https://musicbrainz.org/ws/2"), h = /* @__PURE__ */ P(!1), g = /* @__PURE__ */ P(""), _ = /* @__PURE__ */ P(!1);
	Mr(async () => {
		await v(), F(r, !1);
	});
	async function v() {
		try {
			let e = await (await fetch(`${n()}/accounts`)).json();
			e && (F(i, e.accounts || []), F(a, e.redirect_uri || ""), l = e.client_id_configured || !1, u = e.client_secret_configured || !1, F(p, !!Y(a)));
			let t = await (await fetch(`${n()}/settings`)).json();
			t?.settings && F(m, t.settings.api_base_url || "https://musicbrainz.org/ws/2");
			let r = await (await fetch(`${n()}/credentials`)).json();
			r?.credentials && (F(o, r.credentials.client_id || ""), F(c, u ? "••••••••" : ""));
		} catch (e) {
			console.error("Failed to load MusicBrainz data:", e);
		}
	}
	async function y() {
		if (!Y(o).trim()) {
			console.error("Client ID is required");
			return;
		}
		let e = { client_id: Y(o) };
		if (Y(s).trim()) e.client_secret = Y(s);
		else if (!u) {
			console.error("Client Secret is required");
			return;
		}
		try {
			F(f, !0), await fetch(`${n()}/credentials`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ credentials: e })
			}), F(s, ""), await v();
		} catch (e) {
			console.error("Failed to save credentials:", e);
		} finally {
			F(f, !1);
		}
	}
	async function b() {
		try {
			await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ settings: { api_base_url: Y(m) } })
			}), console.log("MusicBrainz settings saved");
		} catch (e) {
			console.error("Failed to save settings:", e);
		}
	}
	function x() {
		F(g, ""), F(h, !0);
	}
	function S() {
		F(h, !1), F(g, "");
	}
	async function C() {
		let e = Y(g).trim();
		if (e) try {
			F(_, !0), await fetch(`${n()}/accounts`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ account_name: e })
			}), S(), await v();
		} catch (e) {
			console.error("Failed to add account:", e);
		} finally {
			F(_, !1);
		}
	}
	async function w(e, t) {
		if (confirm(`Delete account "${t}"?`)) try {
			await fetch(`${n()}/accounts/${e}`, { method: "DELETE" }), await v();
		} catch (e) {
			console.error("Failed to delete account:", e);
		}
	}
	async function ee(e, t) {
		try {
			await fetch(`${n()}/accounts/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), await v();
		} catch (e) {
			console.error("Failed to update account status:", e);
		}
	}
	async function te(e) {
		if (!l || !u) {
			alert("Save your Client ID and Secret first.");
			return;
		}
		try {
			let t = (await (await fetch(`${n()}/auth?account_id=${e}`)).json())?.auth_url;
			t && (window.open(t, "_blank", "noopener,noreferrer"), setTimeout(() => v(), 5e3));
		} catch (e) {
			console.error("Failed to start OAuth:", e);
		}
	}
	var ne = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), yt();
		}
	};
	li();
	var T = ki(), re = ln(T), ie = R(L(re), 2), ae = (e) => {
		$(e, yi());
	}, oe = (e) => {
		var t = Di(), n = ln(t), r = R(L(n), 2), l = L(r), u = R(L(l), 2);
		$r(u), ze(2), k(l);
		var h = R(l, 2);
		k(r), k(n);
		var g = R(n, 2), _ = R(L(g), 2), v = L(_), S = R(L(v), 2);
		$r(S), k(v);
		var C = R(v, 2), ne = R(L(C), 2), T = L(ne);
		$r(T);
		var re = R(T, 2), ie = L(re, !0);
		k(re), k(ne), k(C);
		var ae = R(C, 2), oe = L(ae, !0);
		k(ae), k(_), k(g);
		var se = R(g, 2), ce = L(se), le = R(L(ce), 2), ue = L(le, !0);
		k(le), k(ce);
		var de = R(ce, 2), fe = (e) => {
			var t = bi(), n = L(t);
			$r(n);
			var r = R(n, 2);
			k(t), An(() => ei(n, Y(a))), Z("click", r, () => {
				navigator.clipboard.writeText(Y(a)), alert("Copied!");
			}), $(e, t);
		};
		Pr(de, (e) => {
			Y(p) || e(fe);
		}), k(se);
		var pe = R(se, 2), me = L(pe), he = L(me), ge = L(he);
		k(he);
		var _e = R(he, 2), ve = (e) => {
			var t = xi();
			Z("click", t, x), $(e, t);
		};
		Pr(_e, (e) => {
			Y(i), X(() => Y(i).length < 10) && e(ve);
		}), k(me);
		var ye = R(me, 2);
		zr(ye, 5, () => Y(i), Fr, (e, t) => {
			var n = Ti(), r = L(n), i = L(r), a = L(i, !0);
			k(i);
			var o = R(i, 2), s = L(o), c = (e) => {
				$(e, Si());
			}, l = (e) => {
				$(e, Ci());
			};
			Pr(s, (e) => {
				Y(t), X(() => Y(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = R(s, 2), d = (e) => {
				$(e, wi());
			};
			Pr(u, (e) => {
				Y(t), X(() => Y(t).is_active) && e(d);
			}), k(o), k(r);
			var f = R(r, 2), p = L(f), m = L(p, !0);
			k(p);
			var h = R(p, 2);
			let g;
			var _ = L(h, !0);
			k(h);
			var v = R(h, 2);
			k(f), k(n), An(() => {
				wr(a, (Y(t), X(() => Y(t).display_name || Y(t).account_name))), wr(m, (Y(t), X(() => Y(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), g = Jr(h, 1, "btn-ghost svelte-1ghyjz5", null, g, { active: Y(t).is_active }), wr(_, (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate")));
			}), Z("click", p, () => te(Y(t).id)), Z("click", h, () => ee(Y(t).id, Y(t).is_active)), Z("click", v, () => w(Y(t).id, Y(t).display_name || Y(t).account_name)), $(e, n);
		}, (e) => {
			$(e, Ei());
		}), k(ye), k(pe), An(() => {
			ti(T, "type", Y(d) ? "text" : "password"), ti(T, "placeholder", Y(c) || "Enter Client Secret"), wr(ie, Y(d) ? "🙈" : "👁️"), ae.disabled = Y(f), wr(oe, Y(f) ? "Saving..." : "Save Credentials"), wr(ue, Y(p) ? "Expand" : "Collapse"), wr(ge, `Accounts (${(Y(i), X(() => Y(i).length)) ?? ""}/10)`);
		}), ai(u, () => Y(m), (e) => F(m, e)), Z("click", h, b), ai(S, () => Y(o), (e) => F(o, e)), ai(T, () => Y(s), (e) => F(s, e)), Z("click", re, () => F(d, !Y(d))), Z("click", ae, y), Z("click", le, () => F(p, !Y(p))), $(e, t);
	};
	Pr(ie, (e) => {
		Y(r) ? e(ae) : e(oe, -1);
	}), k(re);
	var se = R(re, 2), ce = (e) => {
		var n = Oi(), r = L(n), i = L(r), a = R(L(i), 2);
		k(i);
		var o = R(i, 2), s = L(o), c = R(L(s), 2);
		$r(c), k(s), k(o);
		var l = R(o, 2), u = L(l), d = R(u, 2);
		k(l), k(r), k(n), An(() => d.disabled = Y(_)), Z("click", a, S), ai(c, () => Y(g), (e) => F(g, e)), Z("click", u, S), Z("click", d, C), Z("click", r, ci(function(e) {
			di.call(this, t, e);
		})), Z("click", n, S), $(e, n);
	};
	return Pr(se, (e) => {
		Y(h) && e(ce);
	}), $(e, T), qe(ne);
}
customElements.define("musicbrainz-dashboard-card", vi(ji, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
//#region MusicBrainzSettingsCard.svelte
var Mi = /* @__PURE__ */ Q("<div class=\"loading-state svelte-18cwlk6\">Loading configuration…</div>"), Ni = /* @__PURE__ */ Q("<span class=\"status-tag success svelte-18cwlk6\">● Configured</span>"), Pi = /* @__PURE__ */ Q("<div class=\"warning-box svelte-18cwlk6\">⚠ A User Token is required to enable contributions. Please enter your token above.</div>"), Fi = /* @__PURE__ */ Q("<div class=\"feedback error svelte-18cwlk6\"> </div>"), Ii = /* @__PURE__ */ Q("<div class=\"feedback success svelte-18cwlk6\">✓ Configuration saved successfully.</div>"), Li = /* @__PURE__ */ Q("<div class=\"info-banner svelte-18cwlk6\"><p>MusicBrainz works out-of-the-box for metadata retrieval. An account is only needed for contributing data back to the community.</p></div> <div class=\"form-section svelte-18cwlk6\"><label class=\"field-label svelte-18cwlk6\" for=\"mb-user-token\">User Token / API Key <!></label> <p class=\"helper-text svelte-18cwlk6\">Obtain your personal access token from <a href=\"https://musicbrainz.org/account/applications\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"link svelte-18cwlk6\">musicbrainz.org/account/applications</a>.\n        Required for submitting ISRC codes and metadata corrections.</p> <div class=\"input-wrapper svelte-18cwlk6\"><input id=\"mb-user-token\" class=\"input-field svelte-18cwlk6\"/> <button type=\"button\" class=\"toggle-btn svelte-18cwlk6\"> </button></div></div> <div class=\"toggle-card svelte-18cwlk6\"><div class=\"toggle-header svelte-18cwlk6\"><p class=\"toggle-label svelte-18cwlk6\">Auto-Contribute Missing Data</p> <button type=\"button\" role=\"switch\" aria-label=\"Toggle auto-contribute\"><span class=\"switch-thumb svelte-18cwlk6\"></span></button></div> <p class=\"helper-text mt-2 svelte-18cwlk6\">When enabled, EchoSync will automatically submit missing acoustic fingerprints (AcoustID) and \n        ISRC data back to MusicBrainz during imports.</p> <!></div> <!> <!> <div class=\"actions svelte-18cwlk6\"><button class=\"btn-primary svelte-18cwlk6\"> </button></div>", 1), Ri = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-18cwlk6\"><div class=\"card-header svelte-18cwlk6\"><svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"accent-icon svelte-18cwlk6\"><circle cx=\"12\" cy=\"12\" r=\"10\"></circle><path d=\"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3\"></path><line x1=\"12\" y1=\"17\" x2=\"12.01\" y2=\"17\"></line></svg> <div><h2 class=\"card-title svelte-18cwlk6\">MusicBrainz Configuration</h2> <p class=\"card-subtitle svelte-18cwlk6\">Global music encyclopedia & metadata source</p></div> <span class=\"type-badge svelte-18cwlk6\">Metadata</span></div> <!></section>"), zi = {
	hash: "svelte-18cwlk6",
	code: ".plugin-card.svelte-18cwlk6 {background:var(--bg-surface);backdrop-filter:blur(12px);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);padding:24px;margin-bottom:16px;color:var(--text-primary);}.card-header.svelte-18cwlk6 {display:flex;align-items:center;gap:12px;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle);}.accent-icon.svelte-18cwlk6 {color:var(--color-primary);}.card-title.svelte-18cwlk6 {margin:0;font-size:1.25rem;font-weight:600;line-height:1.2;}.card-subtitle.svelte-18cwlk6 {margin:4px 0 0;font-size:0.75rem;color:var(--text-muted);}.type-badge.svelte-18cwlk6 {margin-left:auto;font-size:11px;padding:4px 8px;background:rgba(16, 185, 129, 0.1);color:#10b981;border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-18cwlk6 {padding:20px;text-align:center;color:var(--text-muted);}.info-banner.svelte-18cwlk6 {margin-bottom:24px;padding:12px 16px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle);border-radius:8px;font-size:0.8125rem;color:var(--text-muted);line-height:1.4;}.form-section.svelte-18cwlk6 {margin-bottom:24px;}.field-label.svelte-18cwlk6 {display:block;font-size:0.875rem;font-weight:500;margin-bottom:4px;}.status-tag.success.svelte-18cwlk6 {margin-left:8px;font-size:11px;padding:2px 6px;background:rgba(16, 185, 129, 0.15);color:#10b981;border-radius:4px;}.helper-text.svelte-18cwlk6 {font-size:0.75rem;color:var(--text-muted);margin-bottom:8px;line-height:1.5;}.link.svelte-18cwlk6 {color:var(--color-primary);text-decoration:none;}.link.svelte-18cwlk6:hover {text-decoration:underline;}.input-wrapper.svelte-18cwlk6 {position:relative;display:flex;align-items:center;}.input-field.svelte-18cwlk6 {width:100%;padding:10px 14px;padding-right:40px;background:rgba(0, 0, 0, 0.2);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);color:var(--text-primary);font-size:0.875rem;transition:border-color 0.2s;}.input-field.svelte-18cwlk6:focus {outline:none;border-color:var(--color-primary);}.toggle-btn.svelte-18cwlk6 {position:absolute;right:12px;background:transparent;border:none;cursor:pointer;font-size:1.1rem;opacity:0.6;transition:opacity 0.2s;}.toggle-btn.svelte-18cwlk6:hover {opacity:1;}.toggle-card.svelte-18cwlk6 {margin-bottom:24px;padding:16px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);}.toggle-header.svelte-18cwlk6 {display:flex;justify-content:space-between;align-items:center;}.toggle-label.svelte-18cwlk6 {margin:0;font-size:0.875rem;font-weight:600;}.switch.svelte-18cwlk6 {position:relative;width:44px;height:24px;background:rgba(255, 255, 255, 0.2);border-radius:999px;border:none;cursor:pointer;transition:background 0.2s;}.switch.active.svelte-18cwlk6 {background:var(--color-primary, #14b8a6);}.switch-thumb.svelte-18cwlk6 {position:absolute;top:2px;left:2px;width:20px;height:20px;background:white;border-radius:50%;transition:transform 0.2s;}.switch.active.svelte-18cwlk6 .switch-thumb:where(.svelte-18cwlk6) {transform:translateX(20px);}.warning-box.svelte-18cwlk6 {margin-top:12px;padding:8px 12px;background:rgba(245, 158, 11, 0.1);border:1px solid rgba(245, 158, 11, 0.2);border-radius:6px;font-size:11px;color:#fbbf24;line-height:1.4;}.feedback.svelte-18cwlk6 {margin-bottom:16px;padding:10px 14px;border-radius:var(--radius, 12px);font-size:0.875rem;}.feedback.error.svelte-18cwlk6 {background:rgba(239, 68, 68, 0.1);border:1px solid #ef4444;color:#ef4444;}.feedback.success.svelte-18cwlk6 {background:rgba(16, 185, 129, 0.1);border:1px solid #10b981;color:#10b981;}.actions.svelte-18cwlk6 {display:flex;justify-content:flex-end;}.btn-primary.svelte-18cwlk6 {padding:10px 24px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);font-weight:600;border:none;border-radius:var(--radius, 12px);cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-18cwlk6:hover:not(:disabled) {opacity:0.9;box-shadow:0 4px 12px rgba(20, 184, 166, 0.2);}.btn-primary.svelte-18cwlk6:active:not(:disabled) {transform:scale(0.98);}.btn-primary.svelte-18cwlk6:disabled {opacity:0.5;cursor:not-allowed;}.mt-2.svelte-18cwlk6 {margin-top:8px;}"
};
function Bi(e, t) {
	Ke(t, !1), Gr(e, zi);
	let n = fi(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(!0), i = /* @__PURE__ */ P(!1), a = /* @__PURE__ */ P(!1), o = /* @__PURE__ */ P(""), s = /* @__PURE__ */ P(""), c = /* @__PURE__ */ P(!1), l = /* @__PURE__ */ P(!1), u = /* @__PURE__ */ P(!1);
	Mr(async () => {
		await d(), F(r, !1);
	});
	async function d() {
		try {
			n();
			let e = await fetch(`${n()}/config`);
			if (e.ok) {
				let t = await e.json();
				F(c, t.token_configured ?? !1), F(u, t.auto_contribute ?? !1), Y(c) && F(s, "");
			}
		} catch (e) {
			console.error("[MusicBrainzSettingsCard] Failed to load config:", e);
		}
	}
	async function f() {
		let e = { auto_contribute: Y(u) };
		if (Y(s).trim()) e.user_token = Y(s).trim();
		else if (Y(u) && !Y(c)) {
			F(o, "A User Token is required to enable auto-contributions.");
			return;
		}
		F(o, ""), F(i, !0), F(a, !1);
		try {
			n();
			let t = await fetch(`${n()}/config`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			});
			t.ok ? (F(c, (await t.json()).token_configured ?? Y(c)), F(s, ""), F(a, !0), dispatchEvent(new CustomEvent("musicbrainz-config-saved", {
				bubbles: !0,
				composed: !0,
				detail: {
					auto_contribute: Y(u),
					token_configured: Y(c)
				}
			})), setTimeout(() => F(a, !1), 3e3)) : F(o, (await t.json().catch(() => ({}))).error || "Failed to save configuration.");
		} catch (e) {
			console.error("[MusicBrainzSettingsCard] Save error:", e), F(o, "Network error while saving. Please try again.");
		} finally {
			F(i, !1);
		}
	}
	var p = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), yt();
		}
	};
	li();
	var m = Ri(), h = R(L(m), 2), g = (e) => {
		$(e, Mi());
	}, _ = (e) => {
		var t = Li(), n = R(ln(t), 2), r = L(n), d = R(L(r)), p = (e) => {
			$(e, Ni());
		};
		Pr(d, (e) => {
			Y(c) && e(p);
		}), k(r);
		var m = R(r, 4), h = L(m);
		$r(h);
		var g = R(h, 2), _ = L(g, !0);
		k(g), k(m), k(n);
		var v = R(n, 2), y = L(v), b = R(L(y), 2);
		k(y);
		var x = R(y, 4), S = (e) => {
			$(e, Pi());
		};
		Pr(x, (e) => {
			Y(u) && !Y(c) && !Y(s) && e(S);
		}), k(v);
		var C = R(v, 2), w = (e) => {
			var t = Fi(), n = L(t);
			k(t), An(() => wr(n, `⚠ ${Y(o) ?? ""}`)), $(e, t);
		};
		Pr(C, (e) => {
			Y(o) && e(w);
		});
		var ee = R(C, 2), te = (e) => {
			$(e, Ii());
		};
		Pr(ee, (e) => {
			Y(a) && e(te);
		});
		var ne = R(ee, 2), T = L(ne), re = L(T, !0);
		k(T), k(ne), An(() => {
			ti(h, "type", Y(l) ? "text" : "password"), ti(h, "placeholder", Y(c) ? "••••••••  (leave blank to keep current)" : "Enter your MusicBrainz user token"), ti(g, "title", Y(l) ? "Hide token" : "Show token"), ti(g, "aria-label", Y(l) ? "Hide token" : "Show token"), wr(_, Y(l) ? "🙈" : "👁️"), ti(b, "aria-checked", Y(u)), Jr(b, 1, `switch ${Y(u) ? "active" : ""}`, "svelte-18cwlk6"), T.disabled = Y(i), wr(re, Y(i) ? "Saving…" : "Save Settings");
		}), ai(h, () => Y(s), (e) => F(s, e)), Z("click", g, () => F(l, !Y(l))), Z("click", b, () => F(u, !Y(u))), Z("click", T, f), $(e, t);
	};
	return Pr(h, (e) => {
		Y(r) ? e(g) : e(_, -1);
	}), k(m), $(e, m), qe(p);
}
customElements.define("musicbrainz-settings-card", vi(Bi, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion

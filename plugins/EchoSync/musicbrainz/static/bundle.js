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
var r = {}, i = Symbol(), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, v = () => {};
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
var S = 1024, C = 2048, w = 4096, ee = 8192, te = 16384, ne = 32768, T = 1 << 25, re = 65536, ie = 1 << 19, ae = 1 << 20, oe = 1 << 25, se = 65536, ce = 1 << 21, le = 1 << 22, ue = 1 << 23, de = Symbol("$state"), fe = Symbol("legacy props"), pe = Symbol(""), E = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), me = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function he(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function ge() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function _e(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function ve(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function ye() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function be(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function xe() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Se() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Ce(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function we() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Te() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ee() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function De() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Oe() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function ke(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Ae() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var D = !1;
function je(e) {
	D = e;
}
var O;
function k(e) {
	if (e === null) throw ke(), r;
	return O = e;
}
function Me() {
	return k(/* @__PURE__ */ $t(O));
}
function A(e) {
	if (D) {
		if (/* @__PURE__ */ $t(O) !== null) throw ke(), r;
		O = e;
	}
}
function Ne(e = 1) {
	if (D) {
		for (var t = e, n = O; t--;) n = /* @__PURE__ */ $t(n);
		O = n;
	}
}
function Pe(e = !0) {
	for (var t = 0, n = O;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ $t(n);
		e && n.remove(), n = i;
	}
}
function Fe(e) {
	if (!e || e.nodeType !== 8) throw ke(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Ie(e) {
	return e === this.v;
}
function Le(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Re(e) {
	return !Le(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var j = null;
function ze(e) {
	j = e;
}
function Be(e, n = !1, r) {
	j = {
		p: j,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: W,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Ve(e) {
	var t = j, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) gn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, j = t.p, e ?? {};
}
function He() {
	return !t || j !== null && j.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Ue = [];
function We() {
	var e = Ue;
	Ue = [], b(e);
}
function Ge(e) {
	if (Ue.length === 0 && !at) {
		var t = Ue;
		queueMicrotask(() => {
			t === Ue && We();
		});
	}
	Ue.push(e);
}
function Ke() {
	for (; Ue.length > 0;) We();
}
function qe(e) {
	var t = W;
	if (t === null) return H.f |= ue, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Je(e, t);
}
function Je(e, t) {
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
var Ye = ~(C | w | S);
function M(e, t) {
	e.f = e.f & Ye | t;
}
function Xe(e) {
	e.f & 512 || e.deps === null ? M(e, S) : M(e, w);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function Ze(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= se, Ze(t.deps));
}
function Qe(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), Ze(e.deps), M(e, S);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var $e = !1, et = !1;
function tt(e) {
	var t = et;
	try {
		return et = !1, [e(), et];
	} finally {
		et = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var nt = /* @__PURE__ */ new Set(), N = null, rt = null, P = null, it = null, at = !1, ot = !1, st = null, ct = null, lt = 0, ut = 1, dt = class t {
	id = ut++;
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#e = /* @__PURE__ */ new Set();
	#t = /* @__PURE__ */ new Set();
	#n = /* @__PURE__ */ new Set();
	#r = /* @__PURE__ */ new Map();
	#i = /* @__PURE__ */ new Map();
	#a = null;
	#o = [];
	#s = [];
	#c = /* @__PURE__ */ new Set();
	#l = /* @__PURE__ */ new Set();
	#u = /* @__PURE__ */ new Map();
	#d = /* @__PURE__ */ new Set();
	is_fork = !1;
	#f = !1;
	#p = /* @__PURE__ */ new Set();
	#m() {
		return this.is_fork || this.#i.size > 0;
	}
	#h() {
		for (let n of this.#p) for (let r of n.#i.keys()) {
			for (var e = !1, t = r; t.parent !== null;) {
				if (this.#u.has(t)) {
					e = !0;
					break;
				}
				t = t.parent;
			}
			if (!e) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#u.has(e) || this.#u.set(e, {
			d: [],
			m: []
		}), this.#d.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#u.get(e);
		if (n) {
			this.#u.delete(e);
			for (var r of n.d) M(r, C), t(r);
			for (r of n.m) M(r, w), t(r);
		}
		this.#d.add(e);
	}
	#g() {
		if (lt++ > 1e3 && (nt.delete(this), pt()), !this.#m()) {
			for (let e of this.#c) this.#l.delete(e), M(e, C), this.schedule(e);
			for (let e of this.#l) M(e, w), this.schedule(e);
		}
		let n = this.#o;
		this.#o = [], this.apply();
		var r = st = [], i = [], a = ct = [];
		for (let e of n) try {
			this.#_(e, r, i);
		} catch (t) {
			throw bt(e), t;
		}
		if (N = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (st = null, ct = null, this.#m() || this.#h()) {
			this.#v(i), this.#v(r);
			for (let [e, t] of this.#u) yt(e, t);
		} else {
			this.#r.size === 0 && nt.delete(this), this.#c.clear(), this.#l.clear();
			for (let e of this.#e) e(this);
			this.#e.clear(), rt = this, ht(i), ht(r), rt = null, this.#a?.resolve();
		}
		var s = N;
		if (this.#o.length > 0) {
			let e = s ??= this;
			e.#o.push(...this.#o.filter((t) => !e.#o.includes(t)));
		}
		s !== null && (nt.add(s), s.#g()), e && !nt.has(this) && this.#y();
	}
	#_(t, n, r) {
		t.f ^= S;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#u.has(i)) && i.fn !== null) {
				o ? i.f ^= S : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : Jn(i) && (a & 16 && this.#l.add(i), $n(i));
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
	#v(e) {
		for (var t = 0; t < e.length; t += 1) Qe(e[t], this.#c, this.#l);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), P?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		N = this;
	}
	deactivate() {
		N = null, P = null;
	}
	flush() {
		try {
			ot = !0, N = this, this.#g();
		} finally {
			lt = 0, it = null, st = null, ct = null, ot = !1, N = null, P = null, Rt.clear();
		}
	}
	discard() {
		for (let e of this.#t) e(this);
		this.#t.clear(), this.#n.clear(), nt.delete(this);
	}
	register_created_effect(e) {
		this.#s.push(e);
	}
	#y() {
		for (let l of nt) {
			var e = l.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (l.current.has(r)) {
					var n = l.current.get(r)[0];
					if (e && i !== n) l.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			var r = [...l.current.keys()].filter((e) => !this.current.has(e));
			if (r.length === 0) e && l.discard();
			else if (t.length > 0) {
				if (e) for (let e of this.#d) l.unskip_effect(e, (e) => {
					e.f & 4194320 ? l.schedule(e) : l.#v([e]);
				});
				l.activate();
				var i = /* @__PURE__ */ new Set(), a = /* @__PURE__ */ new Map();
				for (var o of t) gt(o, r, i, a);
				a = /* @__PURE__ */ new Map();
				var s = [...l.current.keys()].filter((e) => this.current.has(e) ? this.current.get(e)[0] !== e : !0);
				for (let e of this.#s) !(e.f & 155648) && _t(e, s, a) && (e.f & 4194320 ? (M(e, C), l.schedule(e)) : l.#c.add(e));
				if (l.#o.length > 0) {
					l.apply();
					for (var c of l.#o) l.#_(c, [], []);
					l.#o = [];
				}
				l.deactivate();
			}
		}
		for (let e of nt) e.#p.has(this) && (e.#p.delete(this), e.#p.size === 0 && !e.#m() && (e.activate(), e.#g()));
	}
	increment(e, t) {
		let n = this.#r.get(t) ?? 0;
		if (this.#r.set(t, n + 1), e) {
			let e = this.#i.get(t) ?? 0;
			this.#i.set(t, e + 1);
		}
	}
	decrement(e, t, n) {
		let r = this.#r.get(t) ?? 0;
		if (r === 1 ? this.#r.delete(t) : this.#r.set(t, r - 1), e) {
			let e = this.#i.get(t) ?? 0;
			e === 1 ? this.#i.delete(t) : this.#i.set(t, e - 1);
		}
		this.#f || n || (this.#f = !0, Ge(() => {
			this.#f = !1, this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#c.add(t);
		for (let e of t) this.#l.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#e.add(e);
	}
	ondiscard(e) {
		this.#t.add(e);
	}
	on_fork_commit(e) {
		this.#n.add(e);
	}
	run_fork_commit_callbacks() {
		for (let e of this.#n) e(this);
		this.#n.clear();
	}
	settled() {
		return (this.#a ??= x()).promise;
	}
	static ensure() {
		if (N === null) {
			let e = N = new t();
			ot || (nt.add(N), at || Ge(() => {
				N === e && e.flush();
			}));
		}
		return N;
	}
	apply() {
		if (!e || !this.is_fork && nt.size === 1) {
			P = null;
			return;
		}
		P = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) P.set(e, t);
		for (let e of nt) if (!(e === this || e.is_fork)) {
			var t = !1, n = !1;
			if (e.id < this.id) for (let [r, [, i]] of e.current) i || (t ||= this.current.has(r), n ||= !this.current.has(r));
			if (t && n) this.#p.add(e);
			else for (let [t, n] of e.previous) P.has(t) || P.set(t, n);
		}
	}
	schedule(t) {
		if (it = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (st !== null && n === W && (e || (H === null || !(H.f & 2)) && !$e)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= S;
			}
		}
		this.#o.push(n);
	}
};
function ft(e) {
	var t = at;
	at = !0;
	try {
		var n;
		for (e && (N !== null && !N.is_fork && N.flush(), n = e());;) {
			if (Ke(), N === null) return n;
			N.flush();
		}
	} finally {
		at = t;
	}
}
function pt() {
	try {
		xe();
	} catch (e) {
		Je(e, it);
	}
}
var mt = null;
function ht(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Jn(r) && (mt = /* @__PURE__ */ new Set(), $n(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && kn(r), mt?.size > 0)) {
				Rt.clear();
				for (let e of mt) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) mt.has(n) && (mt.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || $n(n);
					}
				}
				mt.clear();
			}
		}
		mt = null;
	}
}
function gt(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? gt(i, t, n, r) : e & 4194320 && !(e & 2048) && _t(i, t, r) && (M(i, C), vt(i));
	}
}
function _t(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && _t(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function vt(e) {
	N.schedule(e);
}
function yt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), M(e, S);
		for (var n = e.first; n !== null;) yt(n, t), n = n.next;
	}
}
function bt(e) {
	M(e, S);
	for (var t = e.first; t !== null;) bt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function xt(e) {
	let t = 0, n = Bt(0), r;
	return () => {
		pn() && (Y(n), Sn(() => (t === 0 && (r = X(() => e(() => Wt(n)))), t += 1, () => {
			Ge(() => {
				--t, t === 0 && (r?.(), r = void 0, Wt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var St = re | ie;
function Ct(e, t, n, r) {
	new wt(e, t, n, r);
}
var wt = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = D ? O : null;
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
	#h = xt(() => (this.#m = Bt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = W;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = W.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = wn(() => {
			if (D) {
				let e = this.#t;
				Me();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, St), D && (this.#e = O);
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
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), Ge(() => {
			var e = this.#c = document.createDocumentFragment(), t = L();
			e.append(t), this.#a = this.#x(() => B(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, An(this.#o, () => {
				this.#o = null;
			}), this.#b(N));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Pn(this.#a, e);
				let t = this.#n.pending;
				this.#o = B(() => t(this.#e));
			} else this.#b(N);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		Qe(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = W, n = H, r = j;
		Bn(this.#i), U(this.#i), ze(this.#i.ctx);
		try {
			return dt.ensure(), e();
		} catch (e) {
			return qe(e), null;
		} finally {
			Bn(t), U(n), ze(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && An(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Ge(() => {
			this.#d = !1, this.#m && Ht(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Y(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		N?.is_fork ? (this.#a && N.skip_effect(this.#a), this.#o && N.skip_effect(this.#o), this.#s && N.skip_effect(this.#s), N.on_fork_commit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), D && (k(this.#t), Ne(), k(Pe()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Ae();
				return;
			}
			r = !0, i && De(), this.#s !== null && An(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				Je(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return B(() => {
						var t = W;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return Je(e, this.#i.parent), null;
				}
			}));
		};
		Ge(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				Je(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => Je(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function Tt(e, t, n, r) {
	let i = He() ? kt : jt;
	var a = e.filter((e) => !e.settled);
	if (n.length === 0 && a.length === 0) {
		r(t.map(i));
		return;
	}
	var o = W, s = Et(), c = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function l(e) {
		s();
		try {
			r(e);
		} catch (e) {
			o.f & 16384 || Je(e, o);
		}
		Dt();
	}
	if (n.length === 0) {
		c.then(() => l(t.map(i)));
		return;
	}
	var u = Ot();
	function d() {
		Promise.all(n.map((e) => /* @__PURE__ */ At(e))).then((e) => l([...t.map(i), ...e])).catch((e) => Je(e, o)).finally(() => u());
	}
	c ? c.then(() => {
		s(), d(), Dt();
	}) : d();
}
function Et() {
	var e = W, t = H, n = j, r = N;
	return function(i = !0) {
		Bn(e), U(t), ze(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function Dt(e = !0) {
	Bn(null), U(null), ze(null), e && N?.deactivate();
}
function Ot() {
	var e = W, t = e.b, n = N, r = t.is_rendered();
	return t.update_pending_count(1, n), n.increment(r, e), (i = !1) => {
		t.update_pending_count(-1, n), n.decrement(r, e, i);
	};
}
/* @__NO_SIDE_EFFECTS__ */
function kt(e) {
	var t = 2 | C;
	return W !== null && (W.f |= ie), {
		ctx: j,
		deps: null,
		effects: null,
		equals: Ie,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: W,
		ac: null
	};
}
/* @__NO_SIDE_EFFECTS__ */
function At(e, t, n) {
	let r = W;
	r === null && ge();
	var a = void 0, o = Bt(i), s = !H, c = /* @__PURE__ */ new Map();
	return xn(() => {
		var t = W, n = x();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, n.reject).finally(Dt);
		} catch (e) {
			n.reject(e), Dt();
		}
		var i = N;
		if (s) {
			if (t.f & 32768) var l = Ot();
			if (r.b.is_rendered()) c.get(i)?.reject(E), c.delete(i);
			else {
				for (let e of c.values()) e.reject(E);
				c.clear();
			}
			c.set(i, n);
		}
		let u = (e, n = void 0) => {
			if (l && l(n === E), !(n === E || t.f & 16384)) {
				if (i.activate(), n) o.f |= ue, Ht(o, n);
				else {
					o.f & 8388608 && (o.f ^= ue), Ht(o, e);
					for (let [e, t] of c) {
						if (c.delete(e), e === i) break;
						t.reject(E);
					}
				}
				i.deactivate();
			}
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), mn(() => {
		for (let e of c.values()) e.reject(E);
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
function jt(e) {
	let t = /* @__PURE__ */ kt(e);
	return t.equals = Re, t;
}
function Mt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function Nt(e) {
	var t, n = W, r = e.parent;
	if (!Ln && r !== null && r.f & 24576) return Oe(), e.v;
	Bn(r);
	try {
		e.f &= ~se, Mt(e), t = Xn(e);
	} finally {
		Bn(n);
	}
	return t;
}
function Pt(e) {
	var t = Nt(e);
	if (!e.equals(t) && (e.wv = qn(), (!N?.is_fork || e.deps === null) && (N === null ? e.v = t : N.capture(e, t, !0), e.deps === null))) {
		M(e, S);
		return;
	}
	Ln || (P === null ? Xe(e) : (pn() || N?.is_fork) && P.set(e, t));
}
function Ft(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(E), t.teardown = v, t.ac = null, Qn(t, 0), En(t));
}
function It(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && $n(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Lt = /* @__PURE__ */ new Set(), Rt = /* @__PURE__ */ new Map(), zt = !1;
function Bt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Ie,
		rv: 0,
		wv: 0
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Vt(e, t) {
	let n = Bt(e, t);
	return Vn(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function F(e, n = !1, r = !0) {
	let i = Bt(e);
	return n || (i.equals = Re), t && r && j !== null && j.l !== null && (j.l.s ??= []).push(i), i;
}
function I(e, t, n = !1) {
	return H !== null && (!zn || H.f & 131072) && He() && H.f & 4325394 && (G === null || !c.call(G, e)) && Ee(), Ht(e, n ? Kt(t) : t, ct);
}
function Ht(e, t, n = null) {
	if (!e.equals(t)) {
		Rt.set(e, Ln ? t : e.v);
		var r = dt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Nt(t), P === null && Xe(t);
		}
		e.wv = qn(), Gt(e, C, n), He() && W !== null && W.f & 1024 && !(W.f & 96) && (J === null ? Hn([e]) : J.push(e)), !r.is_fork && Lt.size > 0 && !zt && Ut();
	}
	return t;
}
function Ut() {
	zt = !1;
	for (let e of Lt) e.f & 1024 && M(e, w), Jn(e) && $n(e);
	Lt.clear();
}
function Wt(e) {
	I(e, e.v + 1);
}
function Gt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = He(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === W)) {
			var l = (c & C) === 0;
			if (l && M(s, t), c & 2) {
				var u = s;
				P?.delete(u), c & 65536 || (c & 512 && (W === null || !(W.f & 2097152)) && (s.f |= se), Gt(u, w, n));
			} else if (l) {
				var d = s;
				c & 16 && mt !== null && mt.add(d), n === null ? vt(d) : n.push(d);
			}
		}
	}
}
function Kt(e) {
	if (typeof e != "object" || !e || de in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ Vt(0), s = null, c = Gn, l = (e) => {
		if (Gn === c) return e();
		var t = H, n = Gn;
		U(null), Kn(c);
		var r = e();
		return U(t), Kn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ Vt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && we();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Vt(r.value, s);
				return n.set(t, e), e;
			}) : I(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Vt(i, s));
					n.set(t, e), Wt(a);
				}
			} else I(r, i), Wt(a);
			return !0;
		},
		get(t, r, a) {
			if (r === de) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ Vt(Kt(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
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
			return (r !== void 0 || W !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ Vt(a ? Kt(e[t]) : i, s)), n.set(t, r)), Y(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Vt(i, s)), n.set(p + "", m)) : I(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Vt(void 0, s)), I(u, Kt(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => Kt(o));
				I(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && I(_, v + 1);
				}
				Wt(a);
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
			Te();
		}
	});
}
var qt, Jt, Yt, Xt;
function Zt() {
	if (qt === void 0) {
		qt = window, Jt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Yt = f(t, "firstChild").get, Xt = f(t, "nextSibling").get, _(e) && (e.__click = void 0, e.__className = void 0, e.__attributes = null, e.__style = void 0, e.__e = void 0), _(n) && (n.__t = void 0);
	}
}
function L(e = "") {
	return document.createTextNode(e);
}
/* @__NO_SIDE_EFFECTS__ */
function Qt(e) {
	return Yt.call(e);
}
/* @__NO_SIDE_EFFECTS__ */
function $t(e) {
	return Xt.call(e);
}
function R(e, t) {
	if (!D) return /* @__PURE__ */ Qt(e);
	var n = /* @__PURE__ */ Qt(O);
	if (n === null) n = O.appendChild(L());
	else if (t && n.nodeType !== 3) {
		var r = L();
		return n?.before(r), k(r), r;
	}
	return t && an(n), k(n), n;
}
function en(e, t = !1) {
	if (!D) {
		var n = /* @__PURE__ */ Qt(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ $t(n) : n;
	}
	if (t) {
		if (O?.nodeType !== 3) {
			var r = L();
			return O?.before(r), k(r), r;
		}
		an(O);
	}
	return O;
}
function z(e, t = 1, n = !1) {
	let r = D ? O : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ $t(r);
	if (!D) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = L();
			return r === null ? i?.after(a) : r.before(a), k(a), a;
		}
		an(r);
	}
	return k(r), r;
}
function tn(e) {
	e.textContent = "";
}
function nn() {
	return !e || mt !== null ? !1 : (W.f & ne) !== 0;
}
function rn(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function an(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var on = !1;
function sn() {
	on || (on = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t.__on_r?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function cn(e) {
	var t = H, n = W;
	U(null), Bn(null);
	try {
		return e();
	} finally {
		U(t), Bn(n);
	}
}
function ln(e, t, n, r = n) {
	e.addEventListener(t, () => cn(n));
	let i = e.__on_r;
	i ? e.__on_r = () => {
		i(), r(!0);
	} : e.__on_r = () => r(!0), sn();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function un(e) {
	W === null && (H === null && be(e), ye()), Ln && ve(e);
}
function dn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function fn(e, t) {
	var n = W;
	n !== null && n.f & 8192 && (e |= ee);
	var r = {
		ctx: j,
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
	N?.register_created_effect(r);
	var i = r;
	if (e & 4) st === null ? dt.ensure().schedule(r) : st.push(r);
	else if (t !== null) {
		try {
			$n(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= re));
	}
	if (i !== null && (i.parent = n, n !== null && dn(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function pn() {
	return H !== null && !zn;
}
function mn(e) {
	let t = fn(8, null);
	return M(t, S), t.teardown = e, t;
}
function hn(e) {
	un("$effect");
	var t = W.f;
	if (!H && t & 32 && !(t & 32768)) {
		var n = j;
		(n.e ??= []).push(e);
	} else return gn(e);
}
function gn(e) {
	return fn(4 | ae, e);
}
function _n(e) {
	return un("$effect.pre"), fn(8 | ae, e);
}
function vn(e) {
	dt.ensure();
	let t = fn(64 | ie, e);
	return () => {
		V(t);
	};
}
function yn(e) {
	dt.ensure();
	let t = fn(64 | ie, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? An(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function bn(e) {
	return fn(4, e);
}
function xn(e) {
	return fn(le | ie, e);
}
function Sn(e, t = 0) {
	return fn(8 | t, e);
}
function Cn(e, t = [], n = [], r = []) {
	Tt(r, t, n, (t) => {
		fn(8, () => e(...t.map(Y)));
	});
}
function wn(e, t = 0) {
	return fn(16 | t, e);
}
function B(e) {
	return fn(32 | ie, e);
}
function Tn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = Ln, n = H;
		Rn(!0), U(null);
		try {
			t.call(null);
		} finally {
			Rn(e), U(n);
		}
	}
}
function En(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && cn(() => {
			e.abort(E);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function Dn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (On(e.nodes.start, e.nodes.end), n = !0), M(e, T), En(e, t && !n), Qn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Tn(e), e.f ^= T, e.f |= te;
	var i = e.parent;
	i !== null && i.first !== null && kn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function On(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ $t(e);
		e.remove(), e = n;
	}
}
function kn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function An(e, t, n = !0) {
	var r = [];
	jn(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function jn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ee;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				jn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Mn(e) {
	Nn(e, !0);
}
function Nn(e, t) {
	if (e.f & 8192) {
		e.f ^= ee, e.f & 1024 || (M(e, C), dt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Nn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Pn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ $t(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Fn = null, In = !1, Ln = !1;
function Rn(e) {
	Ln = e;
}
var H = null, zn = !1;
function U(e) {
	H = e;
}
var W = null;
function Bn(e) {
	W = e;
}
var G = null;
function Vn(t) {
	H !== null && (!e || H.f & 2) && (G === null ? G = [t] : G.push(t));
}
var K = null, q = 0, J = null;
function Hn(e) {
	J = e;
}
var Un = 1, Wn = 0, Gn = Wn;
function Kn(e) {
	Gn = e;
}
function qn() {
	return ++Un;
}
function Jn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~se), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Jn(a) && Pt(a), a.wv > e.wv) return !0;
		}
		t & 512 && P === null && M(e, S);
	}
	return !1;
}
function Yn(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && G !== null && c.call(G, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Yn(o, n, !1) : n === o && (r ? M(o, C) : o.f & 1024 && M(o, w), vt(o));
	}
}
function Xn(e) {
	var t = K, n = q, r = J, i = H, a = G, o = j, s = zn, c = Gn, l = e.f;
	K = null, q = 0, J = null, H = l & 96 ? null : e, G = null, ze(e.ctx), zn = !1, Gn = ++Wn, e.ac !== null && (cn(() => {
		e.ac.abort(E);
	}), e.ac = null);
	try {
		e.f |= ce;
		var u = e.fn, d = u();
		e.f |= ne;
		var f = e.deps, p = N?.is_fork;
		if (K !== null) {
			var m;
			if (p || Qn(e, q), f !== null && q > 0) for (f.length = q + K.length, m = 0; m < K.length; m++) f[q + m] = K[m];
			else e.deps = f = K;
			if (pn() && e.f & 512) for (m = q; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && q < f.length && (Qn(e, q), f.length = q);
		if (He() && J !== null && !zn && f !== null && !(e.f & 6146)) for (m = 0; m < J.length; m++) Yn(J[m], e);
		if (i !== null && i !== e) {
			if (Wn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Wn;
			if (t !== null) for (let e of t) e.rv = Wn;
			J !== null && (r === null ? r = J : r.push(...J));
		}
		return e.f & 8388608 && (e.f ^= ue), d;
	} catch (e) {
		return qe(e);
	} finally {
		e.f ^= ce, K = t, q = n, J = r, H = i, G = a, ze(o), zn = s, Gn = c;
	}
}
function Zn(e, t) {
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
		o.f & 512 && (o.f ^= 512, o.f &= ~se), o.v !== i && Xe(o), Ft(o), Qn(o, 0);
	}
}
function Qn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Zn(e, n[r]);
}
function $n(e) {
	var t = e.f;
	if (!(t & 16384)) {
		M(e, S);
		var n = W, r = In;
		W = e, In = !0;
		try {
			t & 16777232 ? Dn(e) : En(e), Tn(e);
			var i = Xn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Un;
		} finally {
			In = r, W = n;
		}
	}
}
async function er() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), ft();
}
function Y(e) {
	var t = (e.f & 2) != 0;
	if (Fn?.add(e), H !== null && !zn && !(W !== null && W.f & 16384) && (G === null || !c.call(G, e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < Wn && (e.rv = Wn, K === null && n !== null && n[q] === e ? q++ : K === null ? K = [e] : K.push(e));
		else {
			(H.deps ??= []).push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : c.call(r, H) || r.push(H);
		}
	}
	if (Ln && Rt.has(e)) return Rt.get(e);
	if (t) {
		var i = e;
		if (Ln) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || nr(i)) && (a = Nt(i)), Rt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !zn && H !== null && (In || (H.f & 512) != 0), s = (i.f & ne) === 0;
		Jn(i) && (o && (i.f |= 512), Pt(i)), o && !s && (It(i), tr(i));
	}
	if (P?.has(e)) return P.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function tr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (It(t), tr(t));
}
function nr(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Rt.has(t) || t.f & 2 && nr(t)) return !0;
	return !1;
}
function X(e) {
	var t = zn;
	try {
		return zn = !0, e();
	} finally {
		zn = t;
	}
}
function rr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (de in e) ir(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && de in n && ir(n);
		}
	}
}
function ir(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			ir(e[n], t);
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
var ar = Symbol("events"), or = /* @__PURE__ */ new Set(), sr = /* @__PURE__ */ new Set();
function cr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || ur.call(t, e), !e.cancelBubble) return cn(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? Ge(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function Z(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = cr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && mn(() => {
		t.removeEventListener(e, o, a);
	});
}
var lr = null;
function ur(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	lr = e;
	var o = 0, s = lr === e && e[ar];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[ar] = t;
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
		var u = H, f = W;
		U(null), Bn(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[ar]?.[r];
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
			e[ar] = t, delete e.currentTarget, U(u), Bn(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var dr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function fr(e) {
	return dr?.createHTML(e) ?? e;
}
function pr(e) {
	var t = rn("template");
	return t.innerHTML = fr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function mr(e, t) {
	var n = W;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Q(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (D) return mr(O, null), O;
		i === void 0 && (i = pr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ Qt(i)));
		var t = r || Jt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ Qt(t), s = t.lastChild;
			mr(o, s);
		} else mr(t, t);
		return t;
	};
}
function $(e, t) {
	if (D) {
		var n = W;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = O), Me();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var hr = ["touchstart", "touchmove"];
function gr(e) {
	return hr.includes(e);
}
function _r(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e.__t ??= e.nodeValue) && (e.__t = n, e.nodeValue = `${n}`);
}
function vr(e, t) {
	return xr(e, t);
}
function yr(e, t) {
	Zt(), t.intro = t.intro ?? !1;
	let n = t.target, i = D, a = O;
	try {
		for (var o = /* @__PURE__ */ Qt(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ $t(o);
		if (!o) throw r;
		je(!0), k(o);
		let i = xr(e, {
			...t,
			anchor: o
		});
		return je(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && Se(), Zt(), tn(n), je(!1), vr(e, t);
	} finally {
		je(i), k(a);
	}
}
var br = /* @__PURE__ */ new Map();
function xr(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	Zt();
	var u = void 0, d = yn(() => {
		var s = n ?? t.appendChild(L());
		Ct(s, { pending: () => {} }, (t) => {
			Be({});
			var n = j;
			if (o && (n.c = o), a && (i.$$events = a), D && mr(t, null), u = e(t, i) || {}, D && (W.nodes.end = O, O === null || O.nodeType !== 8 || O.data !== "]")) throw ke(), r;
			Ve();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = gr(r);
					for (let e of [t, document]) {
						var a = br.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), br.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, ur, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(or)), sr.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = br.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, ur), r.delete(e), r.size === 0 && br.delete(n)) : r.set(e, i);
			}
			sr.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return Sr.set(u, d), u;
}
var Sr = /* @__PURE__ */ new WeakMap();
function Cr(e, t) {
	let n = Sr.get(e);
	return n ? (Sr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var wr = class {
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
			if (n) Mn(n), this.#r.delete(t);
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
						Pn(r, t), t.append(L()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), An(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = N, r = nn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = L();
			i.append(a), this.#n.set(e, {
				effect: B(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, B(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else D && (this.anchor = O), this.#a(n);
	}
};
function Tr(e) {
	j === null && he("onMount"), t && j.l !== null ? Er(j).m.push(e) : hn(() => {
		let t = X(e);
		if (typeof t == "function") return t;
	});
}
function Er(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Dr(e, t, n = !1) {
	var r;
	D && (r = O, Me());
	var i = new wr(e), a = n ? re : 0;
	function o(e, t) {
		if (D) {
			var n = Fe(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Pe();
				k(a), i.anchor = a, je(!1), i.ensure(e, t), je(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	wn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/each.js
function Or(e, t) {
	return t;
}
function kr(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		An(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Ar(e, l(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var c = r.length === 0 && n !== null;
		if (c) {
			var u = n, d = u.parentNode;
			tn(d), d.append(u), e.items.clear();
		}
		Ar(e, t, !c);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Ar(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= oe, Pn(a, document.createDocumentFragment())) : V(t[i], n);
	}
}
var jr;
function Mr(e, t, n, r, i, a = null) {
	var s = e, c = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = D ? k(/* @__PURE__ */ Qt(u)) : u.appendChild(L());
	}
	D && Me();
	var d = null, f = /* @__PURE__ */ jt(() => {
		var e = n();
		return o(e) ? e : e == null ? [] : l(e);
	}), p, m = /* @__PURE__ */ new Map(), h = !0;
	function g(e) {
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, Pr(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= oe, Ir(d, null, s)) : Mn(d) : An(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: wn(() => {
			p = Y(f);
			var e = p.length;
			let o = !1;
			D && Fe(s) === "[!" != (e === 0) && (s = Pe(), k(s), je(!1), o = !0);
			for (var l = /* @__PURE__ */ new Set(), u = N, v = nn(), y = 0; y < e; y += 1) {
				D && O.nodeType === 8 && O.data === "]" && (s = O, o = !0, je(!1));
				var b = p[y], x = r(b, y), S = h ? null : c.get(x);
				S ? (S.v && Ht(S.v, b), S.i && Ht(S.i, y), v && u.unskip_effect(S.e)) : (S = Fr(c, h ? s : jr ??= L(), b, x, y, i, t, n), h || (S.e.f |= oe), c.set(x, S)), l.add(x);
			}
			if (e === 0 && a && !d && (h ? d = B(() => a(s)) : (d = B(() => a(jr ??= L())), d.f |= oe)), e > l.size && _e("", "", ""), D && e > 0 && k(Pe()), !h) if (m.set(u, l), v) {
				for (let [e, t] of c) l.has(e) || u.skip_effect(t.e);
				u.oncommit(g), u.ondiscard(_);
			} else g(u);
			o && je(!0), Y(f);
		}),
		flags: t,
		items: c,
		pending: m,
		outrogroups: null,
		fallback: d
	};
	h = !1, D && (s = O);
}
function Nr(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function Pr(e, t, n, r, i) {
	var a = (r & 8) != 0, o = t.length, s = e.items, c = Nr(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (Mn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) if (_.f ^= oe, _ === c) Ir(_, null, n);
		else {
			var y = d ? d.next : c;
			_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), Lr(e, d, _), Lr(e, _, y), Ir(_, y, n), d = _, p = [], m = [], c = Nr(d.next);
			continue;
		}
		if (_ !== c) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) Ir(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					Lr(e, S.prev, C.next), Lr(e, d, S), Lr(e, C, b), c = b, d = C, --v, p = [], m = [];
				} else u.delete(_), Ir(_, c, n), Lr(e, _.prev, _.next), Lr(e, _, d === null ? e.effect.first : d.next), Lr(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; c !== null && c !== _;) (u ??= /* @__PURE__ */ new Set()).add(c), m.push(c), c = Nr(c.next);
			if (c === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, c = Nr(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Ar(e, l(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (c !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; c !== null;) !(c.f & 8192) && c !== e.fallback && w.push(c), c = Nr(c.next);
		var ee = w.length;
		if (ee > 0) {
			var te = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.fix();
			}
			kr(e, w, te);
		}
	}
	a && Ge(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function Fr(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Bt(n) : /* @__PURE__ */ F(n, !1, !1) : null, l = o & 2 ? Bt(i) : null;
	return {
		v: c,
		i: l,
		e: B(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Ir(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ $t(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function Lr(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Rr(e, t) {
	bn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = rn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/shared/attributes.js
var zr = [..." 	\n\r\f\xA0\v﻿"];
function Br(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || zr.includes(r[o - 1])) && (s === r.length || zr.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/class.js
function Vr(e, t, n, r, i, a) {
	var o = e.__className;
	if (D || o !== n || o === void 0) {
		var s = Br(n, r, a);
		(!D || s !== e.getAttribute("class")) && (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e.__className = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Hr = Symbol("is custom element"), Ur = Symbol("is html"), Wr = me ? "link" : "LINK", Gr = me ? "progress" : "PROGRESS";
function Kr(e) {
	if (D) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Jr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Jr(e, "checked", null), e.checked = r;
				}
			}
		};
		e.__on_r = n, Ge(n), sn();
	}
}
function qr(e, t) {
	var n = Yr(e);
	n.value === (n.value = t ?? void 0) || e.value === t && (t !== 0 || e.nodeName !== Gr) || (e.value = t ?? "");
}
function Jr(e, t, n, r) {
	var i = Yr(e);
	D && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Wr) || i[t] !== (i[t] = n) && (t === "loading" && (e[pe] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Zr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Yr(e) {
	return e.__attributes ??= {
		[Hr]: e.nodeName.includes("-"),
		[Ur]: e.namespaceURI === a
	};
}
var Xr = /* @__PURE__ */ new Map();
function Zr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Xr.get(t);
	if (n) return n;
	Xr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Qr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	ln(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = $r(t) ? ei(a) : a, r(a), N !== null && i.add(N), await er(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (D && t.defaultValue !== t.value || X(n) == null && t.value) && (r($r(t) ? ei(t.value) : t.value), N !== null && i.add(N)), Sn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? rt : N;
			if (i.has(a)) return;
		}
		$r(t) && r === ei(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function $r(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function ei(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function ti(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function ni(e = !1) {
	let t = j, n = t.l.u;
	if (!n) return;
	let r = () => rr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ kt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Y(i);
	}
	n.b.length && _n(() => {
		ri(t, r), b(n.b);
	}), hn(() => {
		let e = X(() => n.m.map(y));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && hn(() => {
		ri(t, r), b(n.a);
	});
}
function ri(e, t) {
	if (e.l.s) for (let t of e.l.s) Y(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/misc.js
function ii(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of o(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function ai(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = () => (l && (l = !1, c = s ? X(i) : i), c);
	let d;
	if (o) {
		var p = de in e || fe in e;
		d = f(e, n)?.set ?? (p && n in e ? (t) => e[n] = t : void 0);
	}
	var m, h = !1;
	o ? [m, h] = tt(() => e[n]) : m = e[n], m === void 0 && i !== void 0 && (m = u(), d && (a && Ce(n), d(m)));
	var g = a ? () => {
		var t = e[n];
		return t === void 0 ? u() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return g;
	if (d) {
		var _ = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || _ || h) && d(t ? g() : e), e) : g();
		});
	}
	var v = !1, y = (r & 1 ? kt : jt)(() => (v = !1, g()));
	o && Y(y);
	var b = W;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Y(y) : a && o ? Kt(e) : e;
			return I(y, n), v = !0, c !== void 0 && (c = n), e;
		}
		return Ln && v || b.f & 16384 ? y.v : Y(y);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function oi(e) {
	return new si(e);
}
var si = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ F(t, !1, !1);
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
				return I(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? yr : vr)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && ft(), this.#e = i.$$events;
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
			Cr(this.#t);
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
}, ci;
typeof HTMLElement == "function" && (ci = class extends HTMLElement {
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
					let n = rn("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = ui(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = li(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = oi({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = vn(() => {
				Sn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = li(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = li(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
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
function li(e, t, n, r) {
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
function ui(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function di(e, t, n, r, i, a) {
	let o = class extends ci {
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
				n = li(e, n, t), this.$$d[e] = n;
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
var fi = /* @__PURE__ */ Q("<div class=\"loading-state svelte-1ghyjz5\">Loading...</div>"), pi = /* @__PURE__ */ Q("<div class=\"redirect-copy-group svelte-1ghyjz5\"><input type=\"text\" class=\"input-field readonly svelte-1ghyjz5\" readonly=\"\"/> <button class=\"btn-primary svelte-1ghyjz5\">Copy</button></div>"), mi = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-1ghyjz5\">+ Add Account</button>"), hi = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-1ghyjz5\">✓ Authenticated</span>"), gi = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-1ghyjz5\">⚠ Not Authenticated</span>"), _i = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-1ghyjz5\">● Active</span>"), vi = /* @__PURE__ */ Q("<div class=\"account-item svelte-1ghyjz5\"><div class=\"account-info svelte-1ghyjz5\"><div class=\"account-name svelte-1ghyjz5\"> </div> <div class=\"account-badges svelte-1ghyjz5\"><!> <!></div></div> <div class=\"account-actions svelte-1ghyjz5\"><button class=\"link-btn svelte-1ghyjz5\"> </button> <button> </button> <button class=\"btn-danger svelte-1ghyjz5\">✕</button></div></div>"), yi = /* @__PURE__ */ Q("<div class=\"empty-accounts svelte-1ghyjz5\">No accounts linked.</div>"), bi = /* @__PURE__ */ Q("<div class=\"settings-section svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">Server Configuration</h3> <div class=\"form-grid svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">API Base URL</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"https://musicbrainz.org/ws/2\"/> <p class=\"helper-text svelte-1ghyjz5\">Point this to a local MusicBrainz container for offline use.</p></label> <button class=\"btn-primary svelte-1ghyjz5\">Save Settings</button></div></div> <div class=\"settings-section svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">OAuth Credentials</h3> <div class=\"form-grid svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Client ID</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"Enter Client ID\"/></label> <label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Client Secret</span> <div class=\"password-wrapper svelte-1ghyjz5\"><input class=\"input-field svelte-1ghyjz5\"/> <button class=\"toggle-visibility svelte-1ghyjz5\"> </button></div></label> <button class=\"btn-primary svelte-1ghyjz5\"> </button></div></div> <div class=\"settings-section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">Redirect URI</h3> <button class=\"btn-ghost svelte-1ghyjz5\"> </button></div> <!></div> <div class=\"settings-section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\"> </h3> <!></div> <div class=\"accounts-list svelte-1ghyjz5\"></div></div>", 1), xi = /* @__PURE__ */ Q("<div class=\"modal-overlay svelte-1ghyjz5\"><div class=\"modal-content svelte-1ghyjz5\"><div class=\"modal-header svelte-1ghyjz5\"><h3 class=\"modal-title svelte-1ghyjz5\">Add MusicBrainz Account</h3> <button class=\"close-btn svelte-1ghyjz5\">✕</button></div> <div class=\"modal-body svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Display Name</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"My Account\"/></label></div> <div class=\"modal-footer svelte-1ghyjz5\"><button class=\"btn-ghost svelte-1ghyjz5\">Cancel</button> <button class=\"btn-primary svelte-1ghyjz5\">Add</button></div></div></div>"), Si = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-1ghyjz5\"><div class=\"card-header svelte-1ghyjz5\"><div class=\"header-left svelte-1ghyjz5\"><h2 class=\"card-title svelte-1ghyjz5\">MusicBrainz</h2> <span class=\"type-badge svelte-1ghyjz5\">Metadata Provider</span></div></div> <!></section> <!>", 1), Ci = {
	hash: "svelte-1ghyjz5",
	code: ".plugin-card.svelte-1ghyjz5 {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-1ghyjz5 {display:flex;align-items:center;gap:12px;}.card-title.svelte-1ghyjz5 {margin:0;font-size:20px;font-weight:700;}.type-badge.svelte-1ghyjz5 {font-size:11px;padding:4px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-1ghyjz5 {padding:24px;text-align:center;color:var(--text-secondary, #cbd5e1);}.settings-section.svelte-1ghyjz5 {margin-bottom:24px;}.section-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;}.section-title.svelte-1ghyjz5 {margin:0;font-size:16px;font-weight:600;}.form-grid.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.field-label.svelte-1ghyjz5 {font-size:13px;font-weight:500;color:var(--text-secondary, #cbd5e1);}.input-field.svelte-1ghyjz5 {width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-1ghyjz5:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.input-field.readonly.svelte-1ghyjz5 {opacity:0.6;cursor:not-allowed;}.btn-primary.svelte-1ghyjz5 {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-1ghyjz5:hover:not(:disabled) {opacity:0.9;}.btn-primary.svelte-1ghyjz5:disabled {opacity:0.5;cursor:not-allowed;}.btn-ghost.svelte-1ghyjz5 {padding:8px 16px;background:rgba(255, 255, 255, 0.05);border:1px solid rgba(255, 255, 255, 0.1);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.svelte-1ghyjz5:hover {background:rgba(255, 255, 255, 0.1);}.btn-ghost.active.svelte-1ghyjz5 {border-color:var(--color-primary, #14b8a6);color:var(--color-primary, #14b8a6);}.btn-danger.svelte-1ghyjz5 {background:rgba(239, 68, 68, 0.15);color:#ef4444;border:none;padding:8px 12px;border-radius:6px;cursor:pointer;}.helper-text.svelte-1ghyjz5 {font-size:11px;color:var(--text-secondary, #cbd5e1);margin-top:4px;}.redirect-copy-group.svelte-1ghyjz5 {display:flex;gap:8px;align-items:stretch;}.redirect-copy-group.svelte-1ghyjz5 .input-field:where(.svelte-1ghyjz5) {flex:1;font-family:monospace;}.accounts-list.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.account-item.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:rgba(255, 255, 255, 0.03);border:1px solid rgba(255, 255, 255, 0.05);border-radius:8px;}.account-info.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:4px;}.account-name.svelte-1ghyjz5 {font-weight:600;font-size:14px;}.account-badges.svelte-1ghyjz5 {display:flex;gap:8px;}.status-badge.svelte-1ghyjz5 {font-size:10px;padding:2px 6px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-1ghyjz5 {background:rgba(34, 197, 94, 0.15);color:#22c55e;}.status-badge.warning.svelte-1ghyjz5 {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-1ghyjz5 {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.account-actions.svelte-1ghyjz5 {display:flex;gap:12px;align-items:center;}.link-btn.svelte-1ghyjz5 {background:none;border:none;color:var(--color-primary, #14b8a6);font-size:13px;font-weight:600;cursor:pointer;}.link-btn.svelte-1ghyjz5:hover {text-decoration:underline;}.password-wrapper.svelte-1ghyjz5 {position:relative;display:flex;align-items:center;width:100%;}.toggle-visibility.svelte-1ghyjz5 {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.modal-overlay.svelte-1ghyjz5 {position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:1000;backdrop-filter:blur(4px);}.modal-content.svelte-1ghyjz5 {background:#0f1216;border:1px solid var(--border-subtle, #1e293b);border-radius:12px;width:100%;max-width:440px;box-shadow:0 24px 48px rgba(0,0,0,0.5);}.modal-header.svelte-1ghyjz5 {padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;justify-content:space-between;align-items:center;}.modal-title.svelte-1ghyjz5 {margin:0;font-size:16px;font-weight:700;}.close-btn.svelte-1ghyjz5 {background:none;border:none;color:var(--text-secondary, #cbd5e1);font-size:20px;cursor:pointer;}.modal-body.svelte-1ghyjz5 {padding:20px;display:flex;flex-direction:column;gap:16px;}.modal-footer.svelte-1ghyjz5 {padding:16px 20px;border-top:1px solid rgba(255,255,255,0.05);display:flex;justify-content:flex-end;gap:12px;}.empty-accounts.svelte-1ghyjz5 {text-align:center;padding:16px;color:var(--text-secondary, #cbd5e1);font-size:13px;background:rgba(255, 255, 255, 0.02);border-radius:8px;border:1px dashed rgba(255, 255, 255, 0.1);}"
};
function wi(e, t) {
	Be(t, !1), Rr(e, Ci);
	let n = ai(t, "apiBase", 12, ""), r = /* @__PURE__ */ F(!0), i = /* @__PURE__ */ F([]), a = /* @__PURE__ */ F(""), o = /* @__PURE__ */ F(""), s = /* @__PURE__ */ F(""), c = /* @__PURE__ */ F(""), l = !1, u = !1, d = /* @__PURE__ */ F(!1), f = /* @__PURE__ */ F(!1), p = /* @__PURE__ */ F(!1), m = /* @__PURE__ */ F("https://musicbrainz.org/ws/2"), h = /* @__PURE__ */ F(!1), g = /* @__PURE__ */ F(""), _ = /* @__PURE__ */ F(!1);
	Tr(async () => {
		await v(), I(r, !1);
	});
	async function v() {
		try {
			let e = await (await fetch(`${n()}/musicbrainz/accounts`)).json();
			e && (I(i, e.accounts || []), I(a, e.redirect_uri || ""), l = e.client_id_configured || !1, u = e.client_secret_configured || !1, I(p, !!Y(a)));
			let t = await (await fetch(`${n()}/providers/musicbrainz/settings`)).json();
			t?.settings && I(m, t.settings.api_base_url || "https://musicbrainz.org/ws/2");
			let r = await (await fetch(`${n()}/providers/musicbrainz/credentials`)).json();
			r?.credentials && (I(o, r.credentials.client_id || ""), I(c, u ? "••••••••" : ""));
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
			I(f, !0), await fetch(`${n()}/providers/musicbrainz/credentials`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ credentials: e })
			}), I(s, ""), await v();
		} catch (e) {
			console.error("Failed to save credentials:", e);
		} finally {
			I(f, !1);
		}
	}
	async function b() {
		try {
			await fetch(`${n()}/providers/musicbrainz/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ settings: { api_base_url: Y(m) } })
			}), console.log("MusicBrainz settings saved");
		} catch (e) {
			console.error("Failed to save settings:", e);
		}
	}
	function x() {
		I(g, ""), I(h, !0);
	}
	function S() {
		I(h, !1), I(g, "");
	}
	async function C() {
		let e = Y(g).trim();
		if (e) try {
			I(_, !0), await fetch(`${n()}/musicbrainz/accounts`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ account_name: e })
			}), S(), await v();
		} catch (e) {
			console.error("Failed to add account:", e);
		} finally {
			I(_, !1);
		}
	}
	async function w(e, t) {
		if (confirm(`Delete account "${t}"?`)) try {
			await fetch(`${n()}/musicbrainz/accounts/${e}`, { method: "DELETE" }), await v();
		} catch (e) {
			console.error("Failed to delete account:", e);
		}
	}
	async function ee(e, t) {
		try {
			await fetch(`${n()}/musicbrainz/accounts/${e}/activate`, {
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
			let t = (await (await fetch(`${n()}/musicbrainz/auth?account_id=${e}`)).json())?.auth_url;
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
			n(e), ft();
		}
	};
	ni();
	var T = Si(), re = en(T), ie = z(R(re), 2), ae = (e) => {
		$(e, fi());
	}, oe = (e) => {
		var t = bi(), n = en(t), r = z(R(n), 2), l = R(r), u = z(R(l), 2);
		Kr(u), Ne(2), A(l);
		var h = z(l, 2);
		A(r), A(n);
		var g = z(n, 2), _ = z(R(g), 2), v = R(_), S = z(R(v), 2);
		Kr(S), A(v);
		var C = z(v, 2), ne = z(R(C), 2), T = R(ne);
		Kr(T);
		var re = z(T, 2), ie = R(re, !0);
		A(re), A(ne), A(C);
		var ae = z(C, 2), oe = R(ae, !0);
		A(ae), A(_), A(g);
		var se = z(g, 2), ce = R(se), le = z(R(ce), 2), ue = R(le, !0);
		A(le), A(ce);
		var de = z(ce, 2), fe = (e) => {
			var t = pi(), n = R(t);
			Kr(n);
			var r = z(n, 2);
			A(t), Cn(() => qr(n, Y(a))), Z("click", r, () => {
				navigator.clipboard.writeText(Y(a)), alert("Copied!");
			}), $(e, t);
		};
		Dr(de, (e) => {
			Y(p) || e(fe);
		}), A(se);
		var pe = z(se, 2), E = R(pe), me = R(E), he = R(me);
		A(me);
		var ge = z(me, 2), _e = (e) => {
			var t = mi();
			Z("click", t, x), $(e, t);
		};
		Dr(ge, (e) => {
			Y(i), X(() => Y(i).length < 10) && e(_e);
		}), A(E);
		var ve = z(E, 2);
		Mr(ve, 5, () => Y(i), Or, (e, t) => {
			var n = vi(), r = R(n), i = R(r), a = R(i, !0);
			A(i);
			var o = z(i, 2), s = R(o), c = (e) => {
				$(e, hi());
			}, l = (e) => {
				$(e, gi());
			};
			Dr(s, (e) => {
				Y(t), X(() => Y(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = z(s, 2), d = (e) => {
				$(e, _i());
			};
			Dr(u, (e) => {
				Y(t), X(() => Y(t).is_active) && e(d);
			}), A(o), A(r);
			var f = z(r, 2), p = R(f), m = R(p, !0);
			A(p);
			var h = z(p, 2);
			let g;
			var _ = R(h, !0);
			A(h);
			var v = z(h, 2);
			A(f), A(n), Cn(() => {
				_r(a, (Y(t), X(() => Y(t).display_name || Y(t).account_name))), _r(m, (Y(t), X(() => Y(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), g = Vr(h, 1, "btn-ghost svelte-1ghyjz5", null, g, { active: Y(t).is_active }), _r(_, (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate")));
			}), Z("click", p, () => te(Y(t).id)), Z("click", h, () => ee(Y(t).id, Y(t).is_active)), Z("click", v, () => w(Y(t).id, Y(t).display_name || Y(t).account_name)), $(e, n);
		}, (e) => {
			$(e, yi());
		}), A(ve), A(pe), Cn(() => {
			Jr(T, "type", Y(d) ? "text" : "password"), Jr(T, "placeholder", Y(c) || "Enter Client Secret"), _r(ie, Y(d) ? "🙈" : "👁️"), ae.disabled = Y(f), _r(oe, Y(f) ? "Saving..." : "Save Credentials"), _r(ue, Y(p) ? "Expand" : "Collapse"), _r(he, `Accounts (${(Y(i), X(() => Y(i).length)) ?? ""}/10)`);
		}), Qr(u, () => Y(m), (e) => I(m, e)), Z("click", h, b), Qr(S, () => Y(o), (e) => I(o, e)), Qr(T, () => Y(s), (e) => I(s, e)), Z("click", re, () => I(d, !Y(d))), Z("click", ae, y), Z("click", le, () => I(p, !Y(p))), $(e, t);
	};
	Dr(ie, (e) => {
		Y(r) ? e(ae) : e(oe, -1);
	}), A(re);
	var se = z(re, 2), ce = (e) => {
		var n = xi(), r = R(n), i = R(r), a = z(R(i), 2);
		A(i);
		var o = z(i, 2), s = R(o), c = z(R(s), 2);
		Kr(c), A(s), A(o);
		var l = z(o, 2), u = R(l), d = z(u, 2);
		A(l), A(r), A(n), Cn(() => d.disabled = Y(_)), Z("click", a, S), Qr(c, () => Y(g), (e) => I(g, e)), Z("click", u, S), Z("click", d, C), Z("click", r, ti(function(e) {
			ii.call(this, t, e);
		})), Z("click", n, S), $(e, n);
	};
	return Dr(se, (e) => {
		Y(h) && e(ce);
	}), $(e, T), Ve(ne);
}
customElements.define("musicbrainz-dashboard-card", di(wi, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
//#region MusicBrainzSettingsCard.svelte
var Ti = /* @__PURE__ */ Q("<div class=\"loading-state svelte-18cwlk6\">Loading configuration…</div>"), Ei = /* @__PURE__ */ Q("<span class=\"status-tag success svelte-18cwlk6\">● Configured</span>"), Di = /* @__PURE__ */ Q("<div class=\"warning-box svelte-18cwlk6\">⚠ A User Token is required to enable contributions. Please enter your token above.</div>"), Oi = /* @__PURE__ */ Q("<div class=\"feedback error svelte-18cwlk6\"> </div>"), ki = /* @__PURE__ */ Q("<div class=\"feedback success svelte-18cwlk6\">✓ Configuration saved successfully.</div>"), Ai = /* @__PURE__ */ Q("<div class=\"info-banner svelte-18cwlk6\"><p>MusicBrainz works out-of-the-box for metadata retrieval. An account is only needed for contributing data back to the community.</p></div> <div class=\"form-section svelte-18cwlk6\"><label class=\"field-label svelte-18cwlk6\" for=\"mb-user-token\">User Token / API Key <!></label> <p class=\"helper-text svelte-18cwlk6\">Obtain your personal access token from <a href=\"https://musicbrainz.org/account/applications\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"link svelte-18cwlk6\">musicbrainz.org/account/applications</a>.\n        Required for submitting ISRC codes and metadata corrections.</p> <div class=\"input-wrapper svelte-18cwlk6\"><input id=\"mb-user-token\" class=\"input-field svelte-18cwlk6\"/> <button type=\"button\" class=\"toggle-btn svelte-18cwlk6\"> </button></div></div> <div class=\"toggle-card svelte-18cwlk6\"><div class=\"toggle-header svelte-18cwlk6\"><p class=\"toggle-label svelte-18cwlk6\">Auto-Contribute Missing Data</p> <button type=\"button\" role=\"switch\" aria-label=\"Toggle auto-contribute\"><span class=\"switch-thumb svelte-18cwlk6\"></span></button></div> <p class=\"helper-text mt-2 svelte-18cwlk6\">When enabled, EchoSync will automatically submit missing acoustic fingerprints (AcoustID) and \n        ISRC data back to MusicBrainz during imports.</p> <!></div> <!> <!> <div class=\"actions svelte-18cwlk6\"><button class=\"btn-primary svelte-18cwlk6\"> </button></div>", 1), ji = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-18cwlk6\"><div class=\"card-header svelte-18cwlk6\"><svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"accent-icon svelte-18cwlk6\"><circle cx=\"12\" cy=\"12\" r=\"10\"></circle><path d=\"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3\"></path><line x1=\"12\" y1=\"17\" x2=\"12.01\" y2=\"17\"></line></svg> <div><h2 class=\"card-title svelte-18cwlk6\">MusicBrainz Configuration</h2> <p class=\"card-subtitle svelte-18cwlk6\">Global music encyclopedia & metadata source</p></div> <span class=\"type-badge svelte-18cwlk6\">Metadata</span></div> <!></section>"), Mi = {
	hash: "svelte-18cwlk6",
	code: ".plugin-card.svelte-18cwlk6 {background:var(--bg-surface);backdrop-filter:blur(12px);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);padding:24px;margin-bottom:16px;color:var(--text-primary);}.card-header.svelte-18cwlk6 {display:flex;align-items:center;gap:12px;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle);}.accent-icon.svelte-18cwlk6 {color:var(--color-primary);}.card-title.svelte-18cwlk6 {margin:0;font-size:1.25rem;font-weight:600;line-height:1.2;}.card-subtitle.svelte-18cwlk6 {margin:4px 0 0;font-size:0.75rem;color:var(--text-muted);}.type-badge.svelte-18cwlk6 {margin-left:auto;font-size:11px;padding:4px 8px;background:rgba(16, 185, 129, 0.1);color:#10b981;border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-18cwlk6 {padding:20px;text-align:center;color:var(--text-muted);}.info-banner.svelte-18cwlk6 {margin-bottom:24px;padding:12px 16px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle);border-radius:8px;font-size:0.8125rem;color:var(--text-muted);line-height:1.4;}.form-section.svelte-18cwlk6 {margin-bottom:24px;}.field-label.svelte-18cwlk6 {display:block;font-size:0.875rem;font-weight:500;margin-bottom:4px;}.status-tag.success.svelte-18cwlk6 {margin-left:8px;font-size:11px;padding:2px 6px;background:rgba(16, 185, 129, 0.15);color:#10b981;border-radius:4px;}.helper-text.svelte-18cwlk6 {font-size:0.75rem;color:var(--text-muted);margin-bottom:8px;line-height:1.5;}.link.svelte-18cwlk6 {color:var(--color-primary);text-decoration:none;}.link.svelte-18cwlk6:hover {text-decoration:underline;}.input-wrapper.svelte-18cwlk6 {position:relative;display:flex;align-items:center;}.input-field.svelte-18cwlk6 {width:100%;padding:10px 14px;padding-right:40px;background:rgba(0, 0, 0, 0.2);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);color:var(--text-primary);font-size:0.875rem;transition:border-color 0.2s;}.input-field.svelte-18cwlk6:focus {outline:none;border-color:var(--color-primary);}.toggle-btn.svelte-18cwlk6 {position:absolute;right:12px;background:transparent;border:none;cursor:pointer;font-size:1.1rem;opacity:0.6;transition:opacity 0.2s;}.toggle-btn.svelte-18cwlk6:hover {opacity:1;}.toggle-card.svelte-18cwlk6 {margin-bottom:24px;padding:16px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);}.toggle-header.svelte-18cwlk6 {display:flex;justify-content:space-between;align-items:center;}.toggle-label.svelte-18cwlk6 {margin:0;font-size:0.875rem;font-weight:600;}.switch.svelte-18cwlk6 {position:relative;width:44px;height:24px;background:rgba(255, 255, 255, 0.2);border-radius:999px;border:none;cursor:pointer;transition:background 0.2s;}.switch.active.svelte-18cwlk6 {background:var(--color-primary, #14b8a6);}.switch-thumb.svelte-18cwlk6 {position:absolute;top:2px;left:2px;width:20px;height:20px;background:white;border-radius:50%;transition:transform 0.2s;}.switch.active.svelte-18cwlk6 .switch-thumb:where(.svelte-18cwlk6) {transform:translateX(20px);}.warning-box.svelte-18cwlk6 {margin-top:12px;padding:8px 12px;background:rgba(245, 158, 11, 0.1);border:1px solid rgba(245, 158, 11, 0.2);border-radius:6px;font-size:11px;color:#fbbf24;line-height:1.4;}.feedback.svelte-18cwlk6 {margin-bottom:16px;padding:10px 14px;border-radius:var(--radius, 12px);font-size:0.875rem;}.feedback.error.svelte-18cwlk6 {background:rgba(239, 68, 68, 0.1);border:1px solid #ef4444;color:#ef4444;}.feedback.success.svelte-18cwlk6 {background:rgba(16, 185, 129, 0.1);border:1px solid #10b981;color:#10b981;}.actions.svelte-18cwlk6 {display:flex;justify-content:flex-end;}.btn-primary.svelte-18cwlk6 {padding:10px 24px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);font-weight:600;border:none;border-radius:var(--radius, 12px);cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-18cwlk6:hover:not(:disabled) {opacity:0.9;box-shadow:0 4px 12px rgba(20, 184, 166, 0.2);}.btn-primary.svelte-18cwlk6:active:not(:disabled) {transform:scale(0.98);}.btn-primary.svelte-18cwlk6:disabled {opacity:0.5;cursor:not-allowed;}.mt-2.svelte-18cwlk6 {margin-top:8px;}"
};
function Ni(e, t) {
	Be(t, !1), Rr(e, Mi);
	let n = ai(t, "apiBase", 12, ""), r = /* @__PURE__ */ F(!0), i = /* @__PURE__ */ F(!1), a = /* @__PURE__ */ F(!1), o = /* @__PURE__ */ F(""), s = /* @__PURE__ */ F(""), c = /* @__PURE__ */ F(!1), l = /* @__PURE__ */ F(!1), u = /* @__PURE__ */ F(!1);
	Tr(async () => {
		await d(), I(r, !1);
	});
	async function d() {
		try {
			let e = n() || "", t = await fetch(`${e}/api/plugins/musicbrainz/config`);
			if (t.ok) {
				let e = await t.json();
				I(c, e.token_configured ?? !1), I(u, e.auto_contribute ?? !1), Y(c) && I(s, "");
			}
		} catch (e) {
			console.error("[MusicBrainzSettingsCard] Failed to load config:", e);
		}
	}
	async function f() {
		let e = { auto_contribute: Y(u) };
		if (Y(s).trim()) e.user_token = Y(s).trim();
		else if (Y(u) && !Y(c)) {
			I(o, "A User Token is required to enable auto-contributions.");
			return;
		}
		I(o, ""), I(i, !0), I(a, !1);
		try {
			let t = n() || "", r = await fetch(`${t}/api/plugins/musicbrainz/config`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			});
			r.ok ? (I(c, (await r.json()).token_configured ?? Y(c)), I(s, ""), I(a, !0), dispatchEvent(new CustomEvent("musicbrainz-config-saved", {
				bubbles: !0,
				composed: !0,
				detail: {
					auto_contribute: Y(u),
					token_configured: Y(c)
				}
			})), setTimeout(() => I(a, !1), 3e3)) : I(o, (await r.json().catch(() => ({}))).error || "Failed to save configuration.");
		} catch (e) {
			console.error("[MusicBrainzSettingsCard] Save error:", e), I(o, "Network error while saving. Please try again.");
		} finally {
			I(i, !1);
		}
	}
	var p = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), ft();
		}
	};
	ni();
	var m = ji(), h = z(R(m), 2), g = (e) => {
		$(e, Ti());
	}, _ = (e) => {
		var t = Ai(), n = z(en(t), 2), r = R(n), d = z(R(r)), p = (e) => {
			$(e, Ei());
		};
		Dr(d, (e) => {
			Y(c) && e(p);
		}), A(r);
		var m = z(r, 4), h = R(m);
		Kr(h);
		var g = z(h, 2), _ = R(g, !0);
		A(g), A(m), A(n);
		var v = z(n, 2), y = R(v), b = z(R(y), 2);
		A(y);
		var x = z(y, 4), S = (e) => {
			$(e, Di());
		};
		Dr(x, (e) => {
			Y(u) && !Y(c) && !Y(s) && e(S);
		}), A(v);
		var C = z(v, 2), w = (e) => {
			var t = Oi(), n = R(t);
			A(t), Cn(() => _r(n, `⚠ ${Y(o) ?? ""}`)), $(e, t);
		};
		Dr(C, (e) => {
			Y(o) && e(w);
		});
		var ee = z(C, 2), te = (e) => {
			$(e, ki());
		};
		Dr(ee, (e) => {
			Y(a) && e(te);
		});
		var ne = z(ee, 2), T = R(ne), re = R(T, !0);
		A(T), A(ne), Cn(() => {
			Jr(h, "type", Y(l) ? "text" : "password"), Jr(h, "placeholder", Y(c) ? "••••••••  (leave blank to keep current)" : "Enter your MusicBrainz user token"), Jr(g, "title", Y(l) ? "Hide token" : "Show token"), Jr(g, "aria-label", Y(l) ? "Hide token" : "Show token"), _r(_, Y(l) ? "🙈" : "👁️"), Jr(b, "aria-checked", Y(u)), Vr(b, 1, `switch ${Y(u) ? "active" : ""}`, "svelte-18cwlk6"), T.disabled = Y(i), _r(re, Y(i) ? "Saving…" : "Save Settings");
		}), Qr(h, () => Y(s), (e) => I(s, e)), Z("click", g, () => I(l, !Y(l))), Z("click", b, () => I(u, !Y(u))), Z("click", T, f), $(e, t);
	};
	return Dr(h, (e) => {
		Y(r) ? e(g) : e(_, -1);
	}), A(m), $(e, m), Ve(p);
}
customElements.define("musicbrainz-settings-card", di(Ni, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
